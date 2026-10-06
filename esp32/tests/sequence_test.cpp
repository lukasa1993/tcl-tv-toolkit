#include "../src/sequence.h"
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
using namespace automation;
struct Run {
  Runner runner;
  std::string output;
  std::vector<std::string> events;
  std::vector<uint32_t> commandTimes;
  void tick(uint32_t now) {
    runner.tick(now, [&](const char *s, size_t n) { output.append(s, n); },
      [&](const char *name, int step) {
        events.emplace_back(name);
        if (step >= 0) commandTimes.push_back(now);
      });
  }
};
int main() {
  Profile p;
  p.startMs=200; p.enterMs=1000; p.intervalMs=100; p.settleMs=300; p.count=2;
  strcpy(p.steps[0].command,"version"); p.steps[0].waitMs=500;
  strcpy(p.steps[1].command,"help"); p.steps[1].waitMs=400;
  assert(valid(p)); assert(duration(p)==2400);
  Run r;
  assert(r.runner.start(p,0,false));
  assert(!r.runner.start(p,0,false));
  for (uint32_t t=0;t<2400;++t) r.tick(t);
  assert(r.runner.active());
  r.tick(2400);
  assert(r.runner.phase==COMPLETE);
  assert(r.runner.enters==10);
  assert(r.output==std::string(10,'\r')+"version\rhelp\r");
  assert((r.commandTimes==std::vector<uint32_t>{1500,2000}));
  auto bytes=r.output; r.tick(3000); assert(r.output==bytes); // never repeats
  Run dry;
  assert(dry.runner.start(p,0,true));
  for(uint32_t t=0;t<=2400;++t)dry.tick(t);
  assert(dry.output.empty()); assert(dry.runner.phase==COMPLETE);
  assert(dry.commandTimes==r.commandTimes); assert(dry.runner.enters==10);
  Run stopped;
  stopped.runner.start(p,0,false);
  for(uint32_t t=0;t<500;++t)stopped.tick(t);
  stopped.runner.stop(); bytes=stopped.output;
  for(uint32_t t=500;t<5000;++t)stopped.tick(t);
  assert(stopped.output==bytes && stopped.runner.sent==0 && stopped.runner.phase==STOPPED);
  Run commandStop;
  commandStop.runner.start(p,0,false);
  for(uint32_t t=0;t<=1500;++t)commandStop.tick(t);
  commandStop.runner.stop();
  for(uint32_t t=1501;t<5000;++t)commandStop.tick(t);
  assert(commandStop.runner.sent==1);
  assert(commandStop.output==std::string(10,'\r')+"version\r");
  Profile enterOnly=p; enterOnly.count=0; enterOnly.settleMs=0;
  Run e; e.runner.start(enterOnly,0,false);
  for(uint32_t t=0;t<=1200;++t)e.tick(t);
  assert(e.runner.phase==COMPLETE && e.output==std::string(10,'\r'));
  Profile immediate=p; immediate.startMs=0; immediate.enterMs=0; immediate.settleMs=0;
  immediate.steps[0].waitMs=0; immediate.steps[1].waitMs=0;
  Run z; z.runner.start(immediate,0,false);
  z.tick(0); z.tick(1); z.tick(2);
  assert(z.output=="version\rhelp\r" && z.runner.phase==COMPLETE);
  Run wrap; const uint32_t base=UINT32_MAX-600;
  wrap.runner.start(p,base,false);
  for(uint32_t delta=0;delta<=2400;++delta)wrap.tick(base+delta);
  assert(wrap.output==r.output && wrap.runner.phase==COMPLETE);
  // A stalled loop must not catch up with a flood of Enter bytes or shorten quiet time.
  Run late; late.runner.start(p,0,false); late.tick(200); late.tick(1000);
  assert(late.runner.enters==2); late.tick(1300);
  assert(late.runner.sent==0); late.tick(1599); assert(late.runner.sent==0);
  late.tick(1600); assert(late.runner.sent==1);
  Profile bad=p; bad.intervalMs=0; assert(!valid(bad));
  bad=p; bad.enterMs=120001; assert(!valid(bad));
  bad=p; bad.count=13; assert(!valid(bad));
  bad=p; strcpy(bad.steps[0].command,"version\rreset"); assert(!valid(bad));
  bad=p; bad.steps[0].waitMs=60001; assert(!valid(bad));
  bad=p; memset(bad.steps[0].command,'x',MAX_COMMAND+1); assert(!valid(bad));
  std::cout<<"PASS: timing, intervals, dry run, stop in both phases, no repeat, zero delays, clock rollover, stalls, validation\n";
}
