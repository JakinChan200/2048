#include <stdlib.h> 

typedef uint64_t board_t;
typedef uint16_t row_t;

//store the depth at which the heuristic was recorded as well as the actual heuristic
struct trans_table_entry_t{
    uint8_t depth;
    float heuristic;
};

static const board_t ROW_MASK = 0xFFFFULL;
static const board_t COL_MASK = 0x000F000F000F000FULL;

static inline void printBoard(board_t board) {
    int i,j;
    for(i=0; i<4; i++) {
        for(j=0; j<4; j++) {
            uint8_t powerVal = (board) & 0xf;
            printf("%6u", (powerVal == 0) ? 0 : 1 << powerVal);
            board >>= 4;
        }
        printf("\n");
    }
    printf("\n");
}

static inline board_t unpack_col(row_t row) {
    board_t tmp = row;
    return (tmp | (tmp << 12ULL) | (tmp << 24ULL) | (tmp << 36ULL)) & COL_MASK;
}

static inline row_t reverse_row(row_t row) {
    return (row >> 12) | ((row >> 4) & 0x00F0)  | ((row << 4) & 0x0F00) | (row << 12);
}

/* Functions */
#ifdef __cplusplus
extern "C" {
#endif

int add(int num, int move);
void myprint(void);

void init_tables();

// typedef int (*get_move_func_t)(board_t);
int find_best_move(board_t board);

#ifdef __cplusplus
}
#endif