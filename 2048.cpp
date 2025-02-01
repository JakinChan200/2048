#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <algorithm>
#include <iostream>

#include "2048.h"
#include <map>
typedef std::map<board_t, trans_table_entry_t> trans_table_t;

// struct TrieNode {
//     TrieNode * child[16];
//     trans_table_entry_t table;

//     TrieNode(){
//         table.depth = 0;
//         table.heuristic = 0;
//         for(auto &a : child){ 
//             a = nullptr;
//         }
//     }

//     ~TrieNode() {
//         for (auto &a : child) {
//             if (a != nullptr) {
//                 delete a;
//             }
//         }
//     }

//     void insert(board_t board, uint8_t depth, float heuristic){
//         TrieNode* node = this;
//         for(int i = 0; i < 15; i++){
//             if(node->child[board & 0xf] == nullptr){
//                 node->child[board & 0xf] = new TrieNode;
//             }
//             node = node->child[board & 0xf];
//             board  = board >> 4;
//         }

//         if(node->child[board & 0xf] == nullptr){
//             node->child[board & 0xf] = new TrieNode;
//         }

//         node->child[board & 0xf]->table.depth = depth;
//         node->child[board & 0xf]->table.heuristic = heuristic;
//     }

//     trans_table_entry_t* search(board_t board){
//         TrieNode* node = this;

//         for(int i = 0; i < 15; i++){
//             if(node->child[board & 0xf] == nullptr){
//                 return nullptr;
//             }
//             node = node->child[board & 0xf];
//             board >>= 4;
//         }

//         if(node->child[board & 0xf] == nullptr){
//             return nullptr;
//         }

//         return &node->child[board & 0xf]->table;
//     }
// };

void myprint(){
    printf("hello world\n");
}

int add(int num,  int num2){
    return num + num2;
}

/* MSVC compatibility: undefine max and min macros */
#if defined(max)
#undef max
#endif

#if defined(min)
#undef min
#endif

//flip the rows and cols
static inline board_t transpose(board_t board){
    board_t temp = 0x0ULL;
    temp |= unpack_col(board >>  0 & ROW_MASK);
    temp |= unpack_col(board >> 16 & ROW_MASK) << 4;
    temp |= unpack_col(board >> 32 & ROW_MASK) << 8;
    temp |= unpack_col(board >> 48 & ROW_MASK) << 12;

    return temp;
}

// Count the number of empty positions (= zero nibbles) in a board.
// Precondition: the board cannot be fully empty.
static int count_empty(board_t x){
    if(x == 0){
        return 16;
    }

    //https://stackoverflow.com/questions/38225571/count-number-of-zero-nibbles-in-an-unsigned-64-bit-integer
    //Gather 1s into the 1s position of each 4
    x |= (x >> 1);
    x |= (x >> 2);
    //Zero the other positions and flip the value of the 1s position
    x = ~x & 0x1111111111111111ULL;

    x += x >> 32;
    x += x >> 16;
    x += x >>  8;
    x += x >>  4; 
    return x & 0xf;
}

/* We can perform state lookups one row at a time by using arrays with 65536 entries. */

/* Move tables. Each row or compressed column is mapped to (oldrow^newrow) assuming row/col 0.
 *
 * Thus, the value is 0 if there is no move, and otherwise equals a value that can easily be
 * xor'ed into the current board state to update the board. */
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

void init_tables() {
    for (unsigned row = 0; row < 65536; ++row) {
        unsigned line[4] = {
                (row >>  0) & 0xf,
                (row >>  4) & 0xf,
                (row >>  8) & 0xf,
                (row >> 12) & 0xf
        };

        // Score
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

        // execute a move to the left
        for (int i = 0; i < 3; ++i) {
            int j;
            for (j = i + 1; j < 4; ++j) {
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

        row_left_table [    row] =                row  ^                result;
        row_right_table[rev_row] =            rev_row  ^            rev_result;
        col_up_table   [    row] = unpack_col(    row) ^ unpack_col(    result);
        col_down_table [rev_row] = unpack_col(rev_row) ^ unpack_col(rev_result);
    }
}

static inline board_t execute_move_0(board_t board) {
    board_t ret = board;
    board_t t = transpose(board);
    ret ^= col_up_table[(t >>  0) & ROW_MASK] <<  0;
    ret ^= col_up_table[(t >> 16) & ROW_MASK] <<  4;
    ret ^= col_up_table[(t >> 32) & ROW_MASK] <<  8;
    ret ^= col_up_table[(t >> 48) & ROW_MASK] << 12;
    return ret;
}

static inline board_t execute_move_1(board_t board) {
    board_t ret = board;
    board_t t = transpose(board);
    ret ^= col_down_table[(t >>  0) & ROW_MASK] <<  0;
    ret ^= col_down_table[(t >> 16) & ROW_MASK] <<  4;
    ret ^= col_down_table[(t >> 32) & ROW_MASK] <<  8;
    ret ^= col_down_table[(t >> 48) & ROW_MASK] << 12;
    return ret;
}

static inline board_t execute_move_2(board_t board) {
    board_t ret = board;
    ret ^= board_t(row_left_table[(board >>  0) & ROW_MASK]) <<  0;
    ret ^= board_t(row_left_table[(board >> 16) & ROW_MASK]) << 16;
    ret ^= board_t(row_left_table[(board >> 32) & ROW_MASK]) << 32;
    ret ^= board_t(row_left_table[(board >> 48) & ROW_MASK]) << 48;
    return ret;
}

static inline board_t execute_move_3(board_t board) {
    board_t ret = board;
    ret ^= board_t(row_right_table[(board >>  0) & ROW_MASK]) <<  0;
    ret ^= board_t(row_right_table[(board >> 16) & ROW_MASK]) << 16;
    ret ^= board_t(row_right_table[(board >> 32) & ROW_MASK]) << 32;
    ret ^= board_t(row_right_table[(board >> 48) & ROW_MASK]) << 48;
    return ret;
}

/* Execute a move. */
board_t execute_move(int move, board_t board) {
    switch(move) {
    case 0: // up
        return execute_move_0(board);
    case 1: // down
        return execute_move_1(board);
    case 2: // left
        return execute_move_2(board);
    case 3: // right
        return execute_move_3(board);
    default:
        return ~0ULL;
    }
}

static inline int get_max_rank(board_t board) {
    int maxrank = 0;
    while (board) {
        maxrank = std::max(maxrank, int(board & 0xf));
        board >>= 4;
    }
    return maxrank;
}

static inline int count_distinct_tiles(board_t board) {
    uint16_t bitset = 0;
    while (board) {
        bitset |= 1<<(board & 0xf);
        board >>= 4;
    }

    // Don't count empty tiles.
    bitset >>= 1;

    int count = 0;
    while (bitset) {
        bitset &= bitset - 1;
        count++;
    }
    return count;
}

/* Optimizing the game */

struct eval_state {
    trans_table_t trans_table; // transposition table, to cache previously-seen moves
    // TrieNode* root;
    int maxdepth;
    int curdepth;
    int cachehits;
    unsigned long moves_evaled;
    int depth_limit;

    eval_state() : maxdepth(0), curdepth(0), cachehits(0), moves_evaled(0), depth_limit(0) {
        // root = new TrieNode;
    }
};

// score a single board heuristically
static float score_heur_board(board_t board);
// score a single board actually (adding in the score from spawned 4 tiles)
static float score_board(board_t board);
// score over all possible moves
static float score_move_node(eval_state &state, board_t board, float cprob);
// score over all possible tile choices and placements
static float score_tilechoose_node(eval_state &state, board_t board, float cprob);


static float score_helper(board_t board, const float* table) {
    return table[(board >>  0) & ROW_MASK] +
           table[(board >> 16) & ROW_MASK] +
           table[(board >> 32) & ROW_MASK] +
           table[(board >> 48) & ROW_MASK];
}

static float score_heur_board(board_t board) {
    return score_helper(          board , heur_score_table) +
           score_helper(transpose(board), heur_score_table);
}

static float score_board(board_t board) {
    return score_helper(board, score_table);
}

// Statistics and controls
// cprob: cumulative probability
// don't recurse into a node with a cprob less than this threshold
static const float CPROB_THRESH_BASE = 0.0001f;
static const int CACHE_DEPTH_LIMIT  = 15;

static float score_tilechoose_node(eval_state &state, board_t board, float cprob) { //cprob starts at 1
    if (cprob < CPROB_THRESH_BASE || state.curdepth >= state.depth_limit) { //If below a certain chance of happening or above the depth limit, set as stopping point and return
        state.maxdepth = std::max(state.curdepth, state.maxdepth);
        return score_heur_board(board);
    }

    // if (state.curdepth < CACHE_DEPTH_LIMIT) {
    //     trans_table_entry_t * temp = state.root->search(board);

    //     if(temp != nullptr){
    //         if(temp->depth <= state.curdepth){
    //             state.cachehits++;
    //             return temp->heuristic;
    //         }
    //     }
    // }   
    if (state.curdepth < CACHE_DEPTH_LIMIT) { //Check if it is a previously seen position
        const trans_table_t::iterator &i = state.trans_table.find(board);
        if (i != state.trans_table.end()) {
            trans_table_entry_t entry = i->second;
            /*
            return heuristic from transposition table only if it means that
            the node will have been evaluated to a minimum depth of state.depth_limit.
            This will result in slightly fewer cache hits, but should not impact the
            strength of the ai negatively.
            */
            if(entry.depth <= state.curdepth)
            {
                state.cachehits++;
                return entry.heuristic;
            }
        }
    }

    int num_open = count_empty(board);
    cprob /= num_open;

    float res = 0.0f;
    board_t tmp = board;
    board_t tile_2 = 1;
    while (tile_2) {    //For every open tile, try it
        if ((tmp & 0xf) == 0) {
            res += score_move_node(state, board |  tile_2      , cprob * 0.9f) * 0.9f;
            res += score_move_node(state, board | (tile_2 << 1), cprob * 0.1f) * 0.1f;
        }
        tmp >>= 4;
        tile_2 <<= 4;
    }
    res = res / num_open;

    if (state.curdepth < CACHE_DEPTH_LIMIT) {
        trans_table_entry_t entry = {static_cast<uint8_t>(state.curdepth), res};
        state.trans_table[board] = entry;//
    }

    // uint8_t tempDepth = state.curdepth;
    // if (state.curdepth < CACHE_DEPTH_LIMIT) {
    //     state.root->insert(board, tempDepth, res);
    // }

    return res;
}

//Tries all 4 moves, and calls score_tilechoose_node, and takes the best scoring move, returns best score
static float score_move_node(eval_state &state, board_t board, float cprob) {
    float best = 0.0f;
    state.curdepth++;
    for (int move = 0; move < 4; ++move) {
        board_t newboard = execute_move(move, board);
        state.moves_evaled++;

        if (board != newboard) {
            best = std::max(best, score_tilechoose_node(state, newboard, cprob));
        }
    }
    state.curdepth--;

    return best;
}

//If the move means the board does not change, return 0, otherwise call score_tilechoose_node with the move
static float _score_toplevel_move(eval_state &state, board_t board, int move) {
    board_t newboard = execute_move(move, board);

    if(board == newboard)
        return 0;

    return score_tilechoose_node(state, newboard, 1.0f) + 1e-6;
}

//Decides the depth and calls _score_toplevel_move
float score_toplevel_move(board_t board, int move) {
    float res;
    eval_state state;

    // TrieNode root;
    // uint8_t depth = 2;
    // res = 16;
    // root.insert(board, depth, res);


    state.depth_limit = std::max(3, count_distinct_tiles(board) - 2);

    res = _score_toplevel_move(state, board, move);

    // delete state.root;
    return res;
}

//Tries all 4 moves by calling score_toplevel_move
int find_best_move(board_t board) {
    // printf("%d\n", board);
    int move;
    float best = 0;
    int bestmove = -1;

    // printBoard(board);
    // printf("Current scores: heur %.0f, actual %.0f\n", score_heur_board(board), score_board(board));

    for(move=0; move<4; move++) {
        float res = score_toplevel_move(board, move);

        if(res > best) {
            best = res;
            bestmove = move;
        }
    }

    return bestmove;
}

// int main(int argc, char** argv){
//     init_tables();
//     board_t board = 1114149ULL;

//     printf("%d\n", find_best_move(board));


//     // board = 0x123456789AFCDFFULL;
//     // printBoard(board);

//     // eval_state state;
//     // uint8_t depth = 2;
//     // float res = 16;

//     // state.root->insert(board, depth, res);

//     // trans_table_entry_t *temp = state.root->search(board);

//     // if(temp == nullptr){
//     //     std::cout << "breh" << std::endl;
//     // }
//     // std::cout << temp->depth << " " << temp->heuristic << "\n";
//     return 0;
// }

/*
struct eval_state {
    // trans_table_t trans_table; // transposition table, to cache previously-seen moves
    TrieNode* root;
    int maxdepth;
    int curdepth;
    int cachehits;
    unsigned long moves_evaled;
    int depth_limit;

    eval_state() : maxdepth(0), curdepth(0), cachehits(0), moves_evaled(0), depth_limit(0) {
        // root = new TrieNode;
    }
};

and the insert part covered, it is accessing parts not available

*/

//why are we transposing the table, but not transposing back when moving up and down
//Cause we are doing more operations on it?

//https://discuss.python.org/t/ctypes-can-not-load-dll-in-which-some-struct-has-constructor-or-destructor/60960

//g++ -m64 -shared -o botLib.dll 2048.cpp
//python 2048.py

//g++ -m64 -O4 -shared -o botLib.dll 2048.cpp -static -static-libgcc -static-libstdc++
//python 2048.py