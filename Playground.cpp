#include <vector>
#include <iostream>
#include <stdint.h>
#include <stdlib.h>
#include <algorithm>
#include <cmath>

using namespace std;

typedef uint64_t board_t;
typedef uint16_t row_t;

static const board_t ROW_MASK = 0xFFFFULL;
static const board_t COL_MASK = 0x000F000F000F000FULL;

struct trans_table_entry_t{
    uint8_t depth;
    float heuristic;
};

static inline void printBoard(board_t board){
    for(int i = 0; i < 4; i++){
        for(int j = 0; j < 4; j++){
            uint8_t power = board & 0xf;
            printf("%6u", (power == 0) ? 0 : 1 << power);
            board >>= 4;
        }
        printf("\n");
    }
    printf("\n");
}

struct TrieNode {
    TrieNode * child[16];
    trans_table_entry_t table;
    TrieNode(){
        table.depth = 0;
        table.heuristic = 0;
        for(auto &a : child){ 
            a = nullptr;
        }
    }

    void insert(board_t board, uint8_t depth, float heuristic){
        TrieNode* node = this;
        for(int i = 0; i < 15; i++){
            if(node->child[board & 0xf] == nullptr){
                node->child[board & 0xf] = new TrieNode;
            }
            node = node->child[board & 0xf];
            board  = board >> 4;
        }

        if(node->child[board & 0xf] == nullptr){
            node->child[board & 0xf] = new TrieNode;
        }

        node->child[board & 0xf]->table.depth = depth;
        node->child[board & 0xf]->table.heuristic = heuristic;
    }

    trans_table_entry_t* search(board_t board){
        TrieNode* node = this;

        for(int i = 0; i < 15; i++){
            if(node->child[board & 0xf] == nullptr){
                return nullptr;
            }
            node = node->child[board & 0xf];
            board >>= 4;
        }

        if(node->child[board & 0xf] == nullptr){
            return nullptr;
        }

        return &node->child[board & 0xf]->table;
    }
};

struct eval_state {
    // trans_table_t trans_table; // transposition table, to cache previously-seen moves
    TrieNode* root = new TrieNode;
    int maxdepth;
    int curdepth;
    int cachehits;
    unsigned long moves_evaled;
    int depth_limit;

    eval_state() : maxdepth(0), curdepth(0), cachehits(0), moves_evaled(0), depth_limit(0) {
    }
};

static int count_empty(board_t x){
    if(x == 0){
        return 16;
    }

    //https://stackoverflow.com/questions/38225571/count-number-of-zero-nibbles-in-an-unsigned-64-bit-integer
    x |= (x >> 1);
    x |= (x >> 2);
    x = ~x & 0x1111111111111111ULL;

    x += x >> 32;
    x += x >> 16;
    x += x >>  8;
    x += x >>  4; 
    return x & 0xf;
}

static inline board_t unpack_col(row_t row) {
    board_t tmp = row;
    return (tmp | (tmp << 12ULL) | (tmp << 24ULL) | (tmp << 36ULL)) & COL_MASK;
}

static inline row_t reverse_row(row_t row) {
    return (row >> 12) | ((row >> 4) & 0x00F0)  | ((row << 4) & 0x0F00) | (row << 12);
}

static inline board_t transpose(board_t x)
{
    board_t a1 = x & 0xF0F00F0FF0F00F0FULL;
    board_t a2 = x & 0x0000F0F00000F0F0ULL;
    board_t a3 = x & 0x0F0F00000F0F0000ULL;
    board_t a = a1 | (a2 << 12) | (a3 >> 12);
    board_t b1 = a & 0xFF00FF0000FF00FFULL;
    board_t b2 = a & 0x00FF00FF00000000ULL;
    board_t b3 = a & 0x00000000FF00FF00ULL;
    return b1 | (b2 >> 24) | (b3 << 24);
}

static row_t row_left_table [65536];
static row_t row_right_table[65536];
static board_t col_up_table[65536];
static board_t col_down_table[65536];
static float heur_score_table[65536];
static float score_table[65536];

// Heuristic scoring settings
static const float SCORE_LOST_PENALTY = 200000.0f;
static const float SCORE_MONOTONICITY_POWER = 4.0f;
static const float SCORE_MONOTONICITY_WEIGHT = 47.0f;
static const float SCORE_SUM_POWER = 3.5f;
static const float SCORE_SUM_WEIGHT = 11.0f;
static const float SCORE_MERGES_WEIGHT = 700.0f;
static const float SCORE_EMPTY_WEIGHT = 270.0f;

//Builds all possible results
void init_tables() {
    //For every possible row
    for (unsigned row = 0; row < 65536; ++row) {
        unsigned line[4] = {
                (row >>  0) & 0xf,
                (row >>  4) & 0xf,
                (row >>  8) & 0xf,
                (row >> 12) & 0xf
        };

        // Score
        //Calculate score by adding up (power - 1) * tileValue
        float score = 0.0f;
        for (int i = 0; i < 4; ++i) {
            int rank = line[i];
            if (rank >= 2) {
                // the score is the total sum of the tile and all intermediate merged tiles
                score += (rank - 1) * (1 << rank);
            }
        }
        score_table[row] = score;


        // Heuristic score
        float sum = 0;
        int empty = 0;
        int merges = 0;

        int prev = 0;
        int counter = 0;
        for (int i = 0; i < 4; ++i) {
            int rank = line[i];
            sum += pow(rank, SCORE_SUM_POWER);
            if (rank == 0) {
                empty++;
            } else {
                if (prev == rank) {
                    counter++;
                } else if (counter > 0) {
                    merges += 1 + counter;
                    counter = 0;
                }
                prev = rank;
            }
        }
        if (counter > 0) {
            merges += 1 + counter;
        }

        float monotonicity_left = 0;
        float monotonicity_right = 0;
        for (int i = 1; i < 4; ++i) {
            if (line[i-1] > line[i]) {
                monotonicity_left += pow(line[i-1], SCORE_MONOTONICITY_POWER) - pow(line[i], SCORE_MONOTONICITY_POWER);
            } else {
                monotonicity_right += pow(line[i], SCORE_MONOTONICITY_POWER) - pow(line[i-1], SCORE_MONOTONICITY_POWER);
            }
        }

        heur_score_table[row] = SCORE_LOST_PENALTY +
            SCORE_EMPTY_WEIGHT * empty +
            SCORE_MERGES_WEIGHT * merges -
            SCORE_MONOTONICITY_WEIGHT * std::min(monotonicity_left, monotonicity_right) -
            SCORE_SUM_WEIGHT * sum;

        //From here and below, store every possible output
        // execute a move to the left
        for (int i = 0; i < 3; ++i) {
            int j;
            for (j = i + 1; j < 4; ++j) { //Find the first non-zero tile right of i
                if (line[j] != 0) break;
            }
            if (j == 4) break; // no more tiles to the right

            if (line[i] == 0) {
                line[i] = line[j];
                line[j] = 0;
                i--; // retry this entry
            } else if (line[i] == line[j]) {
                if(line[i] != 0xf) {
                    /* Pretend that 32768 + 32768 = 32768 (representational limit). */
                    line[i]++;
                }
                line[j] = 0;
            }
        }

        row_t result = (line[0] <<  0) |
                       (line[1] <<  4) |
                       (line[2] <<  8) |
                       (line[3] << 12);
        row_t rev_result = reverse_row(result);
        unsigned rev_row = reverse_row(row);

        row_left_table [    row] =                 result; //It looks useless to only store changes, because you need to undo it
        row_right_table[rev_row] =             rev_result;
        col_up_table   [    row] = unpack_col(    result);
        col_down_table [rev_row] = unpack_col(rev_result);
    }
}

static inline board_t execute_move_0(board_t board) {
    board_t t = transpose(board);
    board_t ret = col_up_table[(t >>  0) & ROW_MASK] <<  0 |
                  col_up_table[(t >> 16) & ROW_MASK] <<  4 |
                  col_up_table[(t >> 32) & ROW_MASK] <<  8 |
                  col_up_table[(t >> 48) & ROW_MASK] << 12;
    return ret;
}

static inline void printBits(uint16_t num){
    uint16_t temp = 0;
    for(int i = 0; i < 16; i++){
        temp <<= 1;
        temp += num & 0x1;
        num >>= 1;
    }

    for(int i = 0; i < 16; i++){
        cout << (temp & 0x1); 
        temp >>= 1;

        if(i+1 % 4 == 0){
            cout << " ";
        }
    }
    cout << "\n";
}

static inline int countDistinctTiles(board_t board){
    uint16_t bitset = 0;
    while(board){
        bitset |= 1 << (board & 0xf);
        board >>= 4;
    }

    bitset >>= 1;

    int count = 0;
    while(bitset){ //Brian Kernighan's algorithm 
        printBits(bitset);
        bitset &= bitset - 1;
        count++;
    }
    return count;
}

int main(int argc, char** argv){
    board_t board = 0x123456789AFCDFFULL;
    printBoard(board);

    eval_state state;
    uint8_t depth = 6;
    float res = 16;

    state.root->insert(board, depth, res);

    trans_table_entry_t *temp = state.root->search(board);

    cout << temp->depth << " " << temp->heuristic << "\n";

    // cout << countDistinctTiles(board) << endl;

    // board_t temp = 0x0ULL;
    // temp |= unpack_col(board & 0xFFFFULL);
    // temp |= unpack_col(board & 0xFFFF000ULL) << 4;
    // temp |= unpack_col(board >> 32 & 0xFFFFULL) << 8;
    // temp |= unpack_col(board >> 48 & 0xFFFFULL) << 12;
    // printBoard(temp);

    // init_tables();
    // printBoard(transpose(board));

    // printBoard(execute_move_0(transpose(board)));

    // cout << "answer: " << countEmpty(board);



    return 0;
}