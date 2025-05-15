#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDebug>
#include <QTimer>
#include <QPropertyAnimation>
#include <queue>
#include <vector>

using Call = std::pair<int,int>; // first: floor, second: sequence

struct CompareUp {
    bool operator()(const Call &a, const Call &b) const {
        if (a.first != b.first)
            return a.first > b.first;   // smaller floor first
        return a.second > b.second;     // earlier call first
    }
};

struct CompareDown {
    bool operator()(const Call &a, const Call &b) const {
        if (a.first != b.first)
            return a.first < b.first;   // larger floor first
        return a.second > b.second;
    }
};

// Globals for Elevator 1
int currentFloor1 = 1;
int direction1 = 0; // +1=up, -1=down, 0=idle
int seq1 = 0;
bool isMoving1 = false;
int targetFloor1 = -1;
QTimer *elevatorTimer1 = nullptr;
QTimer *idleReturnTimer1 = nullptr;
std::priority_queue<Call, std::vector<Call>, CompareUp> upQueue1;
std::priority_queue<Call, std::vector<Call>, CompareDown> downQueue1;
std::set<int> intermediateStops1;

// Globals for Elevator 2
int currentFloor2 = 6;
int direction2 = 0;
int seq2 = 0;
bool isMoving2 = false;
int targetFloor2 = -1;
QTimer *elevatorTimer2 = nullptr;
QTimer *idleReturnTimer2 = nullptr;
std::priority_queue<Call, std::vector<Call>, CompareUp> upQueue2;
std::priority_queue<Call, std::vector<Call>, CompareDown> downQueue2;
std::set<int> intermediateStops2;

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    elevator1Anim = new QPropertyAnimation(ui->elevator1Box, "geometry");
    elevator2Anim = new QPropertyAnimation(ui->elevator2Box, "geometry");
    elevator1Anim->setDuration(300);
    elevator2Anim->setDuration(300);
    updateElevatorLabel(currentFloor1, currentFloor2);

    auto connectCall = [&](QPushButton *btn, int floor, bool up) {
        connect(btn, &QPushButton::clicked, [=]() { handleExternalCall(floor, up); });
    };
    connectCall(ui->underFloorUp,    0, true);
    connectCall(ui->firstFloorUp,    1, true);
    connectCall(ui->firstFloorDown,  1, false);
    connectCall(ui->secondFloorUp,   2, true);
    connectCall(ui->secondFloorDown, 2, false);
    connectCall(ui->thirdFloorUp,    3, true);
    connectCall(ui->thirdFloorDown,  3, false);
    connectCall(ui->fourthFloorUp,   4, true);
    connectCall(ui->fourthFloorDown, 4, false);
    connectCall(ui->fifthFloorUp,    5, true);
    connectCall(ui->fifthFloorDown,  5, false);
    connectCall(ui->sixthFloorUp,    6, true);
    connectCall(ui->sixthFloorDown,  6, false);
    connectCall(ui->seventhFloorUp,  7, true);
    connectCall(ui->seventhFloorDown,7, false);
    connectCall(ui->topFloorDown,    8, false);

    elevatorTimer1 = new QTimer(this);
    connect(elevatorTimer1, &QTimer::timeout, this, &MainWindow::moveOneFloor1);
    elevatorTimer2 = new QTimer(this);
    connect(elevatorTimer2, &QTimer::timeout, this, &MainWindow::moveOneFloor2);

    idleReturnTimer1 = new QTimer(this);
    idleReturnTimer1->setSingleShot(true);
    connect(idleReturnTimer1, &QTimer::timeout, this, [=]() {
        if (!isMoving1 && direction1 == 0 && upQueue1.empty() && downQueue1.empty())
            handleExternalCall(1, false);
    });

    idleReturnTimer2 = new QTimer(this);
    idleReturnTimer2->setSingleShot(true);
    connect(idleReturnTimer2, &QTimer::timeout, this, [=]() {
        if (!isMoving2 && direction2 == 0 && upQueue2.empty() && downQueue2.empty())
            handleExternalCall(6, false);
    });
}

MainWindow::~MainWindow() { delete ui; }

void MainWindow::updateElevatorLabel(int floor1, int floor2)
{
    auto getName = [](int floor) {
        switch (floor) {
        case 9: return QString("Top Floor (9)");
        case 8: return QString("Floor 8");
        case 7: return QString("Floor 7");
        case 6: return QString("Floor 6");
        case 5: return QString("Floor 5");
        case 4: return QString("Floor 4");
        case 3: return QString("Floor 3");
        case 2: return QString("Floor 2");
        case 1: return QString("Floor 1");
        default: return QString("Underground (0)");
        }
    };

    auto moveLabel = [](QPropertyAnimation *anim, QWidget *widget, int floor, int xOffset) {
        int baseY = 0;
        int floorHeight = 70;
        int y = baseY + (9 - floor) * floorHeight;

        QRect newGeom(xOffset, y, widget->width(), widget->height());
        anim->stop();
        anim->setStartValue(widget->geometry());
        anim->setEndValue(newGeom);
        int distance = abs(widget->geometry().topLeft().y() - newGeom.topLeft().y());
        int duration = qMax(distance * 5, 100);
        anim->setDuration(duration);
        anim->setEasingCurve(QEasingCurve::InOutQuad);
        anim->start();
    };

    ui->elevator1Box->setText("E1 at: " + getName(floor1));
    ui->elevator2Box->setText("E2 at: " + getName(floor2));

    moveLabel(elevator1Anim, ui->elevator1Box, floor1, 50);
    moveLabel(elevator2Anim, ui->elevator2Box, floor2, 190);
}
bool MainWindow::checkIntermediateStop(int &currentFloor, std::set<int> &stops, QTimer *timer)
{
    if (stops.count(currentFloor)) {
        timer->stop();
        stops.erase(currentFloor);
        updateElevatorLabel(currentFloor1, currentFloor2); // uses global floors
        QTimer::singleShot(500, this, [=]() { timer->start(1000); });
        return true;
    }
    return false;
}

void MainWindow::handleExternalCall(int floor, bool goingUp)
{
    int d1 = abs(currentFloor1 - floor), d2 = abs(currentFloor2 - floor);
    bool idle1 = !isMoving1, idle2 = !isMoving2;
    int choice = (floor <= 4) ? 1 : 2;

    if ((choice == 1 && !idle1) || (choice == 2 && !idle2)) {
        if (idle1 && !idle2) choice = 1;
        else if (!idle1 && idle2) choice = 2;
        else choice = (d1 <= d2) ? 1 : 2;
    }

    if (choice == 1) {
        int seq = seq1++;
        if (isMoving1) {
            if (direction1 == 1 && goingUp && floor > currentFloor1 && floor < targetFloor1) {
                intermediateStops1.insert(floor);
            } else if (direction1 == -1 && !goingUp && floor < currentFloor1 && floor > targetFloor1) {
                intermediateStops1.insert(floor);
            } else {
                if (goingUp) upQueue1.push({floor, seq});
                else downQueue1.push({floor, seq});
            }
        } else {
            if (goingUp) upQueue1.push({floor, seq});
            else downQueue1.push({floor, seq});
        }
        if (!isMoving1) {
            direction1 = goingUp ? +1 : -1;
            processNextRequest1();
        }
    } else {
        int seq = seq2++;
        if (isMoving2) {
            if (direction2 == 1 && goingUp && floor > currentFloor2 && floor < targetFloor2) {
                intermediateStops2.insert(floor);
            } else if (direction2 == -1 && !goingUp && floor < currentFloor2 && floor > targetFloor2) {
                intermediateStops2.insert(floor);
            } else {
                if (goingUp) upQueue2.push({floor, seq});
                else downQueue2.push({floor, seq});
            }
        } else {
            if (goingUp) upQueue2.push({floor, seq});
            else downQueue2.push({floor, seq});
        }
        if (!isMoving2) {
            direction2 = goingUp ? +1 : -1;
            processNextRequest2();
        }
    }
}


void MainWindow::processNextRequest1()
{
    idleReturnTimer1->stop();
    if (upQueue1.empty() && downQueue1.empty()) {
        isMoving1 = false;
        direction1 = 0;
        idleReturnTimer1->start(3000);
        return;
    }
    if (direction1 == +1) {
        if (!upQueue1.empty()) {
            targetFloor1 = upQueue1.top().first;
            upQueue1.pop();
        } else {
            direction1 = -1;
            targetFloor1 = downQueue1.top().first;
            downQueue1.pop();
        }
    } else {
        if (!downQueue1.empty()) {
            targetFloor1 = downQueue1.top().first;
            downQueue1.pop();
        } else {
            direction1 = +1;
            targetFloor1 = upQueue1.top().first;
            upQueue1.pop();
        }
    }
    isMoving1 = true;
    elevatorTimer1->start(800);
}

void MainWindow::processNextRequest2()
{
    idleReturnTimer2->stop();
    if (upQueue2.empty() && downQueue2.empty()) {
        isMoving2 = false;
        direction2 = 0;
        idleReturnTimer2->start(3000);
        return;
    }
    if (direction2 == +1) {
        if (!upQueue2.empty()) {
            targetFloor2 = upQueue2.top().first;
            upQueue2.pop();
        } else {
            direction2 = -1;
            targetFloor2 = downQueue2.top().first;
            downQueue2.pop();
        }
    } else {
        if (!downQueue2.empty()) {
            targetFloor2 = downQueue2.top().first;
            downQueue2.pop();
        } else {
            direction2 = +1;
            targetFloor2 = upQueue2.top().first;
            upQueue2.pop();
        }
    }
    isMoving2 = true;
    elevatorTimer2->start(800);
}

void MainWindow::moveOneFloor1()
{
    if (checkIntermediateStop(currentFloor1, intermediateStops1, elevatorTimer1))
        return;

    if (currentFloor1 == targetFloor1) {
        elevatorTimer1->stop();
        isMoving1 = false;
        updateElevatorLabel(currentFloor1, currentFloor2);
        processNextRequest1();
        return;
    }
    currentFloor1 += (targetFloor1 > currentFloor1) ? 1 : -1;
    updateElevatorLabel(currentFloor1, currentFloor2);
}


void MainWindow::moveOneFloor2()
{
    if (checkIntermediateStop(currentFloor2, intermediateStops2, elevatorTimer2))
        return;

    if (currentFloor2 == targetFloor2) {
        elevatorTimer2->stop();
        isMoving2 = false;
        updateElevatorLabel(currentFloor1, currentFloor2);
        processNextRequest2();
        return;
    }
    currentFloor2 += (targetFloor2 > currentFloor2) ? 1 : -1;
    updateElevatorLabel(currentFloor1, currentFloor2);
}

