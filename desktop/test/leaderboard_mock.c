// Steam flat API の偽物（ランキングだけ）。test/test_leaderboard.js が使う。構造体の並びと関数の形を確かめる
#include <stdint.h>
#include <string.h>
#include <stdbool.h>
#pragma pack(push, 8)
typedef struct { uint64_t h; uint8_t found; } FindResult;
typedef struct { uint64_t h; uint64_t entries; int32_t count; } Downloaded;
typedef struct { uint8_t success; uint64_t h; int32_t score; uint8_t changed; int32_t rankNew, rankPrev; } Uploaded;
typedef struct { uint64_t id; int32_t rank, score, details; uint64_t ugc; } Entry;
#pragma pack(pop)
static int dummy;
static uint64_t BOARD = 0x1122334455667788ULL;
static int32_t best = 0, bestDet[64], bestN = 0, polls = 0;
static uint64_t lastCall = 0; static int lastKind = 0; static char lastName[64];
static uint64_t ME = 76561198000000001ULL, OTHER = 76561198000000002ULL;
void *SteamAPI_SteamUserStats_v012(void) { return &dummy; }
void *SteamAPI_SteamUtils_v010(void) { return &dummy; }
void *SteamAPI_SteamFriends_v017(void) { return &dummy; }
void *SteamAPI_SteamUser_v023(void) { return &dummy; }
uint64_t SteamAPI_ISteamUser_GetSteamID(void *s) { return ME; }
uint64_t SteamAPI_ISteamUserStats_FindOrCreateLeaderboard(void *s, const char *name, int sort, int disp) { strncpy(lastName, name, 63); if (sort != 2 || disp != 1) return 0; polls = 0; lastKind = 1104; return lastCall = 0xA000000000000001ULL; }
uint64_t SteamAPI_ISteamUserStats_UploadLeaderboardScore(void *s, uint64_t h, int method, int32_t score, const int32_t *d, int n) {
  if (h != BOARD || method != 1) return 0;
  static Uploaded u; u.success = 1; u.h = h; u.score = score; u.changed = score > best; u.rankPrev = best ? 2 : 0;
  if (score > best) { best = score; memcpy(bestDet, d, n * 4); bestN = n; } u.rankNew = 1;
  polls = 0; lastKind = 1106; return lastCall = 0xA000000000000002ULL; }
uint64_t SteamAPI_ISteamUserStats_DownloadLeaderboardEntries(void *s, uint64_t h, int req, int a, int b) { if (h != BOARD) return 0; polls = 0; lastKind = 1105; return lastCall = 0xA000000000000003ULL; }
bool SteamAPI_ISteamUserStats_GetDownloadedLeaderboardEntry(void *s, uint64_t entries, int i, Entry *e, int32_t *d, int max) {
  if (entries != 0xBEEF00000000BEEFULL) return false;
  if (i == 0) { e->id = OTHER; e->rank = 1; e->score = 20000; e->details = 2; e->ugc = 0; d[0] = 7; d[1] = 8; return true; }
  e->id = ME; e->rank = 2; e->score = best; e->details = bestN; e->ugc = 0; memcpy(d, bestDet, (bestN < max ? bestN : max) * 4); return true; }
bool SteamAPI_ISteamUtils_IsAPICallCompleted(void *s, uint64_t call, bool *failed) { *failed = false; return call == lastCall && ++polls >= 3; }
bool SteamAPI_ISteamUtils_GetAPICallResult(void *s, uint64_t call, void *out, int size, int expected, bool *failed) {
  *failed = false; if (call != lastCall || expected != lastKind) return false;
  if (expected == 1104) { if (size != sizeof(FindResult)) return false; FindResult r = { BOARD, 1 }; memcpy(out, &r, sizeof r); return true; }
  if (expected == 1106) { if (size != sizeof(Uploaded)) return false; static Uploaded u; u.success = 1; u.h = BOARD; u.score = best; u.changed = 1; u.rankNew = 1; u.rankPrev = 2; memcpy(out, &u, sizeof u); return true; }
  if (expected == 1105) { if (size != sizeof(Downloaded)) return false; Downloaded r = { BOARD, 0xBEEF00000000BEEFULL, 2 }; memcpy(out, &r, sizeof r); return true; }
  return false; }
const char *SteamAPI_ISteamFriends_GetFriendPersonaName(void *s, uint64_t id) { return id == ME ? "しゅん" : "Rival"; }
