#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

namespace automation {
constexpr size_t MAX_STEPS = 12;
constexpr size_t MAX_COMMAND = 256;
struct Step {
  char command[MAX_COMMAND + 1] = {};
  uint32_t waitMs = 2000;
};
struct Profile {
  uint32_t startMs = 0;
  uint32_t enterMs = 10000;
  uint32_t intervalMs = 100;
  uint32_t settleMs = 2000;
  uint8_t count = 1;
  Step steps[MAX_STEPS];
  Profile() { strcpy(steps[0].command, "version"); }
};
inline bool valid(const Profile &p) {
  if (p.startMs > 120000 || p.enterMs > 120000 || p.intervalMs < 20 ||
      p.intervalMs > 1000 || p.settleMs > 30000 || p.count > MAX_STEPS) return false;
  for (size_t i = 0; i < p.count; ++i) {
    size_t n = strnlen(p.steps[i].command, MAX_COMMAND + 1);
    if (!n || n > MAX_COMMAND || p.steps[i].waitMs > 60000) return false;
    for (size_t j = 0; j < n; ++j)
      if (static_cast<unsigned char>(p.steps[i].command[j]) < 32 ||
          static_cast<unsigned char>(p.steps[i].command[j]) > 126) return false;
  }
  return true;
}
inline uint32_t duration(const Profile &p) {
  uint32_t ms = p.startMs + p.enterMs + p.settleMs;
  for (size_t i = 0; i < p.count; ++i) ms += p.steps[i].waitMs;
  return ms;
}
enum Phase { IDLE, START_DELAY, ENTER_BURST, SETTLE, COMMANDS, COMPLETE, STOPPED };
inline const char *phaseName(Phase p) {
  switch (p) {
    case START_DELAY: return "start-delay";
    case ENTER_BURST: return "enter-burst";
    case SETTLE: return "settle";
    case COMMANDS: return "commands";
    case COMPLETE: return "complete";
    case STOPPED: return "stopped";
    default: return "idle";
  }
}
// The caller supplies the clock and writer, so timing is testable without hardware.
class Runner {
 public:
  Profile profile;
  Phase phase = IDLE;
  bool dry = false;
  uint32_t started = 0, deadline = 0, nextEnter = 0, enters = 0;
  uint8_t sent = 0;
  bool active() const { return phase >= START_DELAY && phase <= COMMANDS; }
  void clear() {
    phase = IDLE; dry = false; started = deadline = nextEnter = enters = 0; sent = 0;
  }
  bool start(const Profile &p, uint32_t now, bool dryRun) {
    if (active() || !valid(p)) return false;
    profile = p; dry = dryRun; started = now; enters = 0; sent = 0;
    deadline = now + p.startMs; phase = START_DELAY;
    return true;
  }
  void stop() { if (active()) phase = STOPPED; }
  template <typename Writer, typename Event>
  void tick(uint32_t now, Writer write, Event event) {
    if (!active()) return;
    if (phase == START_DELAY && due(now, deadline)) {
      phase = ENTER_BURST; deadline = now + profile.enterMs; nextEnter = now;
      event("enter-burst", -1);
    }
    if (phase == ENTER_BURST) {
      if (due(now, deadline)) {
        phase = SETTLE; deadline = now + profile.settleMs;
        event("settle", -1);
      } else if (due(now, nextEnter)) {
        if (!dry) write("\r", 1);
        ++enters;
        // Don't replay missed intervals after a delayed loop iteration.
        nextEnter = now + profile.intervalMs;
      }
    }
    if (phase == SETTLE && due(now, deadline)) {
      phase = COMMANDS; deadline = now;
    }
    if (phase == COMMANDS && due(now, deadline)) {
      if (sent == profile.count) {
        phase = COMPLETE; event("complete", -1);
      } else {
        const Step &step = profile.steps[sent];
        if (!dry) { write(step.command, strlen(step.command)); write("\r", 1); }
        event("command", sent);
        ++sent;
        deadline = now + step.waitMs;
      }
    }
  }
 private:
  static bool due(uint32_t now, uint32_t at) { return int32_t(now - at) >= 0; }
};
} // namespace automation
