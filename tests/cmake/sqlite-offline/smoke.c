#include <sqlite3.h>

int main(void) {
  sqlite3 *db = 0;
  sqlite3_stmt *statement = 0;
  if (sqlite3_open(":memory:", &db) != SQLITE_OK) return 1;
  if (sqlite3_exec(db, "CREATE TABLE t(value INTEGER)", 0, 0, 0) != SQLITE_OK)
    return 2;
  if (sqlite3_prepare_v2(db, "INSERT INTO t VALUES(42) RETURNING value", -1,
                         &statement, 0) != SQLITE_OK)
    return 3;
  if (sqlite3_step(statement) != SQLITE_ROW ||
      sqlite3_column_int(statement, 0) != 42)
    return 4;
  if (sqlite3_finalize(statement) != SQLITE_OK) return 5;
  return sqlite3_close(db) == SQLITE_OK ? 0 : 6;
}
