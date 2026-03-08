#include <Windows.h>
#include <QApplication>
#include <QTimer>
#include "demoqt.h"

MainWidget::MainWidget(QWidget* parent)
    : QWidget(parent)
    , m_hcam(nullptr)
    , m_timer(new QTimer(this))
    , m_imgWidth(0), m_imgHeight(0), m_pData(nullptr)
    , m_frame(0), m_count(0)
{
    setMinimumSize(1024, 768);

    QGridLayout* gmain = new QGridLayout();

    QGroupBox* gboxexp = new QGroupBox("Exposure");
    {
        m_cbox_auto = new QCheckBox("Auto exposure");
        m_cbox_auto->setEnabled(false);
        m_lbl_expoTime = new QLabel("0");
        m_lbl_expoGain = new QLabel("0");
        m_slider_expoTime = new QSlider(Qt::Horizontal);
        m_slider_expoGain = new QSlider(Qt::Horizontal);
        m_slider_expoTime->setEnabled(false);
        m_slider_expoGain->setEnabled(false);
        connect(m_cbox_auto, &QCheckBox::stateChanged, this, [this](bool state)
        {
            if (m_hcam)
            {
                Uvcham_put(m_hcam, UVCHAM_AEXPO, state ? 1 : 0);
                m_slider_expoTime->setEnabled(!state);
                m_slider_expoGain->setEnabled(!state);
            }
        });
        connect(m_slider_expoTime, &QSlider::valueChanged, this, [this](int value)
        {
            if (m_hcam)
            {
                m_lbl_expoTime->setText(QString::number(value));
                if (!m_cbox_auto->isChecked())
                   Uvcham_put(m_hcam, UVCHAM_EXPOTIME, value);
            }
        });
        connect(m_slider_expoGain, &QSlider::valueChanged, this, [this](int value)
        {
            if (m_hcam)
            {
                m_lbl_expoGain->setText(QString::number(value));
                if (!m_cbox_auto->isChecked())
                    Uvcham_put(m_hcam, UVCHAM_AGAIN, value);
            }
        });

        QVBoxLayout* v = new QVBoxLayout();
        v->addWidget(m_cbox_auto);
        v->addLayout(makeLayout(new QLabel("Time:"), m_slider_expoTime, m_lbl_expoTime, new QLabel("Gain:"), m_slider_expoGain, m_lbl_expoGain));
        gboxexp->setLayout(v);
    }

    {
        m_btn_autoWB = new QPushButton("White balance");
        m_btn_autoWB->setEnabled(false);
        connect(m_btn_autoWB, &QPushButton::clicked, this, [this]()
        {
            Uvcham_put(m_hcam, UVCHAM_WBMODE, 3);
        });
        m_btn_open = new QPushButton("Open");
        connect(m_btn_open, &QPushButton::clicked, this, &MainWidget::onBtnOpen);
        m_btn_snap = new QPushButton("Snap");
        m_btn_snap->setEnabled(false);
        connect(m_btn_snap, &QPushButton::clicked, this, &MainWidget::onBtnSnap);

        QVBoxLayout* v = new QVBoxLayout();
        v->addWidget(gboxexp);
        v->addWidget(m_btn_autoWB);
        v->addWidget(m_btn_open);
        v->addWidget(m_btn_snap);
        v->addStretch();
        gmain->addLayout(v, 0, 0);
    }

    {
        m_lbl_frame = new QLabel();
        m_lbl_video = new QLabel();

        QVBoxLayout* v = new QVBoxLayout();
        v->addWidget(m_lbl_video, 1);
        v->addWidget(m_lbl_frame);
        gmain->addLayout(v, 0, 1);
    }

    gmain->setColumnStretch(0, 1);
    gmain->setColumnStretch(1, 4);
    setLayout(gmain);

    connect(this, &MainWidget::evtCallback, this, [this](unsigned nEvent)
    {
        /* this run in the UI thread */
        if (m_hcam)
        {
            if (UVCHAM_EVENT_IMAGE & nEvent)
                onImageEvent();
            else if (UVCHAM_EVENT_ERROR & nEvent)
            {
                closeCamera();
                QMessageBox::warning(this, "Warning", "Generic error.");
            }
            else if (UVCHAM_EVENT_DISCONNECT & nEvent)
            {
                closeCamera();
                QMessageBox::warning(this, "Warning", "Camera disconnect.");
            }
        }
    });

    connect(m_timer, &QTimer::timeout, this, [this]()
    {
        if (m_hcam)
        {
            m_lbl_frame->setText(QString::number(m_frame));

            if (m_cbox_auto->isChecked())
            {
                UpdateExpoTime();
                UpdateGain();
            }
        }
    });
}

void MainWidget::UpdateExpoTime()
{
    int val = 0;
    Uvcham_get(m_hcam, UVCHAM_EXPOTIME, &val);
    {
        QSignalBlocker blocker(m_slider_expoTime);
        m_slider_expoTime->setValue(val);
    }
    m_lbl_expoTime->setText(QString::number(val));
}

void MainWidget::UpdateGain()
{
    int val = 0;
    Uvcham_get(m_hcam, UVCHAM_AGAIN, &val);
    {
        QSignalBlocker blocker(m_slider_expoGain);
        m_slider_expoGain->setValue(val);
    }
    m_lbl_expoGain->setText(QString::number(val));
}

void MainWidget::closeCamera()
{
    if (m_hcam)
    {
        Uvcham_close(m_hcam);
        m_hcam = nullptr;
    }
    delete[] m_pData;
    m_pData = nullptr;

    m_btn_open->setText("Open");
    m_timer->stop();
    m_lbl_frame->clear();
    m_cbox_auto->setEnabled(false);
    m_slider_expoGain->setEnabled(false);
    m_slider_expoTime->setEnabled(false);
    m_btn_autoWB->setEnabled(false);
    m_btn_snap->setEnabled(false);
}

void MainWidget::closeEvent(QCloseEvent*)
{
    closeCamera();
}

void MainWidget::openCamera(const wchar_t* id)
{
    m_hcam = Uvcham_open(id);
    if (m_hcam)
    {
        m_frame = 0;
        Uvcham_put(m_hcam, UVCHAM_FORMAT, 2); //Qimage use RGB byte order

        int res = 0;
        Uvcham_get(m_hcam, UVCHAM_RES, &res);
        Uvcham_get(m_hcam, UVCHAM_WIDTH | res, &m_imgWidth);
        Uvcham_get(m_hcam, UVCHAM_HEIGHT | res, &m_imgHeight);
        if (m_pData)
        {
            delete[] m_pData;
            m_pData = nullptr;
        }
        m_pData = new uchar[TDIBWIDTHBYTES(m_imgWidth * 24) * m_imgHeight];
        if (SUCCEEDED(Uvcham_start(m_hcam, nullptr/* Pull Mode */, eventCallBack, this)))
        {
            m_cbox_auto->setEnabled(true);
            m_btn_autoWB->setEnabled(true);
            m_btn_open->setText("Close");
            m_btn_snap->setEnabled(true);

            int bAuto = 0, nmin = 0, nmax = 0, ndef = 0;
            Uvcham_range(m_hcam, UVCHAM_EXPOTIME, &nmin, &nmax, &ndef);
            m_slider_expoTime->setRange(nmin, nmax);
            Uvcham_range(m_hcam, UVCHAM_AGAIN, &nmin, &nmax, &ndef);
            m_slider_expoGain->setRange(nmin, nmax);
            Uvcham_get(m_hcam, UVCHAM_AEXPO, &bAuto);
            m_cbox_auto->setChecked(1 == bAuto);
            m_slider_expoTime->setEnabled(1 != bAuto);
            m_slider_expoGain->setEnabled(1 != bAuto);

            UpdateExpoTime();
            UpdateGain();
            
            m_timer->start(1000);
        }
        else
        {
            closeCamera();
            QMessageBox::warning(this, "Warning", "Failed to start camera.");
        }
    }
}

void MainWidget::onBtnOpen()
{
    if (m_hcam)
        closeCamera();
    else
    {
        UvchamDevice arr[UVCHAM_MAX] = { 0 };
        unsigned count = Uvcham_enum(arr);
        if (0 == count)
            QMessageBox::warning(this, "Warning", "No camera found.");
        else if (1 == count)
            openCamera(arr[0].id);
        else
        {
            QMenu menu;
            for (unsigned i = 0; i < count; ++i)
            {
                menu.addAction(QString::fromWCharArray(arr[i].displayname), this, [this, i, arr](bool)
                {
                    openCamera(arr[i].id);
                });
            }
            menu.exec(mapToGlobal(m_btn_snap->pos()));
        }
    }
}

void MainWidget::onBtnSnap()
{
    if (m_hcam && m_pData)
    {
        QImage image(m_pData, m_imgWidth, m_imgHeight, QImage::Format_RGB888);
        image.save(QString::asprintf("demoqt_%u.jpg", ++m_count));
    }
}

void MainWidget::eventCallBack(unsigned nEvent, void* pCallbackCtx)
{
    MainWidget* pThis = reinterpret_cast<MainWidget*>(pCallbackCtx);
    emit pThis->evtCallback(nEvent);
}

void MainWidget::onImageEvent()
{
	if (SUCCEEDED(Uvcham_pull(m_hcam, m_pData))) /* Pull Mode */
    {
		++m_frame;
		QImage image(m_pData, m_imgWidth, m_imgHeight, QImage::Format_RGB888);
		QImage newimage = image.scaled(m_lbl_video->width(), m_lbl_video->height(), Qt::KeepAspectRatio, Qt::FastTransformation);
		m_lbl_video->setPixmap(QPixmap::fromImage(newimage));
	}
}

QVBoxLayout* MainWidget::makeLayout(QLabel* lbl1, QSlider* sli1, QLabel* val1, QLabel* lbl2, QSlider* sli2, QLabel* val2)
{
    QHBoxLayout* hlyt1 = new QHBoxLayout();
    hlyt1->addWidget(lbl1);
    hlyt1->addStretch();
    hlyt1->addWidget(val1);
    QHBoxLayout* hlyt2 = new QHBoxLayout();
    hlyt2->addWidget(lbl2);
    hlyt2->addStretch();
    hlyt2->addWidget(val2);
    QVBoxLayout* vlyt = new QVBoxLayout();
    vlyt->addLayout(hlyt1);
    vlyt->addWidget(sli1);
    vlyt->addLayout(hlyt2);
    vlyt->addWidget(sli2);
    return vlyt;
}

int main(int argc, char* argv[])
{
    QApplication a(argc, argv);
    MainWidget mw;
    mw.show();
    return a.exec();
}
