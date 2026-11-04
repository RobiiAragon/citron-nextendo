// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <QEventLoop>
#include <QObject>
#include <QThread>

namespace Frontend {

// An emulation thread can already be waiting for a BlockingQueuedConnection
// to the GUI when shutdown begins. Keep delivering those calls until it exits;
// waiting on the GUI thread first would prevent that exit forever.
inline void WaitForThreadWithEvents(QThread& thread) {
    QEventLoop loop;
    const auto connection = QObject::connect(&thread, &QThread::finished, &loop,
                                             &QEventLoop::quit, Qt::QueuedConnection);
    if (!thread.isFinished()) {
        loop.exec(QEventLoop::ExcludeUserInputEvents);
    }
    QObject::disconnect(connection);
    thread.wait();
}

} // namespace Frontend
