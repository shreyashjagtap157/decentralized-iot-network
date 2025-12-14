#ifndef TASK_SCHEDULER_H
#define TASK_SCHEDULER_H

#include <Arduino.h>
#include <vector>
#include <functional>

class TaskScheduler {
public:
    void addTask(uint32_t interval, std::function<void()> task);
    void runTasks();

private:
    struct Task {
        uint32_t interval;
        uint32_t lastRun;
        std::function<void()> task;
    };

    std::vector<Task> tasks;
};

#endif