#ifndef __demoqt_H__
#define __demoqt_H__

#include <QPushButton>
#include <QComboBox>
#include <QLabel>
#include <QTimer>
#include <QCheckBox>
#include <QSlider>
#include <QString>
#include <QGroupBox>
#include <QBoxLayout>
#include <QVBoxLayout>
#include <QMenu>
#include <QMessageBox>
#include <uvcham.h>

class MainWidget : public QWidget
{
    Q_OBJECT
    HUvcham         m_hcam;
    QCheckBox*      m_cbox_auto;
    QSlider*        m_slider_expoTime;
    QSlider*        m_slider_expoGain;
    QLabel*         m_lbl_expoTime;
    QLabel*         m_lbl_expoGain;
    QLabel*         m_lbl_video;
    QLabel*         m_lbl_frame;
    QPushButton*    m_btn_autoWB;
    QPushButton*    m_btn_open;
    QPushButton*    m_btn_snap;
    QTimer*         m_timer;
    int             m_imgWidth;
    int             m_imgHeight;
    uchar*          m_pData;
    unsigned        m_frame;
    unsigned        m_count;
public:
    MainWidget(QWidget* parent = nullptr);
protected:
    void closeEvent(QCloseEvent*) override;
signals:
    void evtCallback(unsigned nEvent);
private:
    void onBtnOpen();
    void onBtnSnap();
    void openCamera(const wchar_t* id);
    void closeCamera();
    void onImageEvent();
    void UpdateExpoTime();
    void UpdateGain();
    static void __stdcall eventCallBack(unsigned nEvent, void* pCallbackCtx);
    static QVBoxLayout* makeLayout(QLabel*, QSlider*, QLabel*, QLabel*, QSlider*, QLabel*);
};

#endif
