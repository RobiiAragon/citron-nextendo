// SPDX-License-Identifier: GPL-2.0-or-later

#include <cassert>
#include <QCoreApplication>
#include <QMetaObject>
#include <QObject>
#include <QSemaphore>
#include <QThread>

#include "citron/thread_shutdown.h"

class Worker final : public QThread {
public:
    QObject receiver;
    QSemaphore entering_call;
    int delivered = 0;

    void run() override {
        entering_call.release();
        const bool invoked = QMetaObject::invokeMethod(
            &receiver, [this] { ++delivered; }, Qt::BlockingQueuedConnection);
        assert(invoked);
    }
};

int main(int argc, char** argv) {
    QCoreApplication application(argc, argv);
    for (int iteration = 0; iteration < 20; ++iteration) {
        Worker worker;
        worker.start();
        worker.entering_call.acquire();
        Frontend::WaitForThreadWithEvents(worker);
        assert(worker.isFinished());
        assert(worker.delivered == 1);
        // A completed worker must not wait for a finished signal a second time.
        Frontend::WaitForThreadWithEvents(worker);
    }
}
