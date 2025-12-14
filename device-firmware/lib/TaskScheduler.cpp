#include "TaskScheduler.h"

void TaskScheduler::addTask(uint32_t interval, std::function<void()> task) {
    tasks.push_back({interval, millis(), task});
}

void TaskScheduler::runTasks() {
    uint32_t currentMillis = millis();
    for (auto& task : tasks) {
        if (currentMillis - task.lastRun >= task.interval) {
            task.task();
            task.lastRun = currentMillis;
        }
    }
}