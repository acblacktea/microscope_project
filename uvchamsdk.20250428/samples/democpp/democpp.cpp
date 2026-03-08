#include <atlbase.h>
#include <atlwin.h>
#include <atlapp.h>
CAppModule _Module;
#include <windows.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <atlctrls.h>
#include <atlframe.h>
#include <atlcrack.h>
#include <atldlgs.h>
#include <atlstr.h>
#include "uvcham.h"
#include "resource.h"
#include <amvideo.h>

#define MSG_CALLBACK	(WM_APP + 1)

class CMainFrame;

void AtlMessageBoxHresult(HWND hWnd, HRESULT hr)
{
	PTCHAR pMsgBuf = NULL;
	FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
		NULL, hr, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (LPTSTR)&pMsgBuf, 0, NULL);
	if (pMsgBuf && pMsgBuf[0])
	{
		AtlMessageBox(hWnd, (LPCTSTR)pMsgBuf);
		LocalFree(pMsgBuf);
	}
	else
	{
		TCHAR str[64] = { 0 };
		_stprintf(str, L"Error, hr = 0x%08x", hr);
		AtlMessageBox(hWnd, str);
	}
}

class CExposureTimeDlg : public CDialogImpl<CExposureTimeDlg>
{
	HUvcham	m_hcam;

	BEGIN_MSG_MAP(CExposureTimeDlg)
		MESSAGE_HANDLER(WM_INITDIALOG, OnInitDialog)
		COMMAND_HANDLER(IDOK, BN_CLICKED, OnOK)
		COMMAND_HANDLER(IDCANCEL, BN_CLICKED, OnCancel)
	END_MSG_MAP()
public:
	enum { IDD = IDD_EXPOSURETIME };
	CExposureTimeDlg(HUvcham hcam)
	: m_hcam(hcam)
	{
	}
private:
	LRESULT OnInitDialog(UINT /*uMsg*/, WPARAM /*wParam*/, LPARAM /*lParam*/, BOOL& /*bHandled*/)
	{
		CenterWindow(GetParent());

		CTrackBarCtrl ctrl(GetDlgItem(IDC_SLIDER1));
		int nmin = 0, nmax = 0, ndef = 0;
		Uvcham_range(m_hcam, UVCHAM_EXPOTIME, &nmin, &nmax, &ndef);
		ctrl.SetRangeMin(nmin);
		ctrl.SetRangeMax(nmax);

		int nTime = 0;
		if (SUCCEEDED(Uvcham_get(m_hcam, UVCHAM_EXPOTIME, &nTime)))
			ctrl.SetPos(nTime);
		
		return TRUE;
	}

	LRESULT OnOK(WORD /*wNotifyCode*/, WORD wID, HWND /*hWndCtl*/, BOOL& /*bHandled*/)
	{
		CTrackBarCtrl ctrl(GetDlgItem(IDC_SLIDER1));
		Uvcham_put(m_hcam, UVCHAM_EXPOTIME, ctrl.GetPos());

		EndDialog(wID);
		return 0;
	}

	LRESULT OnCancel(WORD /*wNotifyCode*/, WORD wID, HWND /*hWndCtl*/, BOOL& /*bHandled*/)
	{
		EndDialog(wID);
		return 0;
	}
};

class CMainView : public CWindowImpl<CMainView>
{
	CMainFrame*	m_pMainFrame;

	BEGIN_MSG_MAP(CMainView)
		MESSAGE_HANDLER(WM_PAINT, OnWmPaint)
		MESSAGE_HANDLER(WM_ERASEBKGND, OnEraseBkgnd)
	END_MSG_MAP()
	static ATL::CWndClassInfo& GetWndClassInfo()
	{
		static ATL::CWndClassInfo wc =
		{
			{ sizeof(WNDCLASSEX), CS_HREDRAW | CS_VREDRAW, StartWindowProc,
			  0, 0, NULL, NULL, NULL, (HBRUSH)NULL_BRUSH, NULL, NULL, NULL },
			NULL, NULL, IDC_ARROW, TRUE, 0, _T("")
		};
		return wc;
	}
public:
	CMainView(CMainFrame* pMainFrame)
	: m_pMainFrame(pMainFrame)
	{
	}
private:
	LRESULT OnWmPaint(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled);
	LRESULT OnEraseBkgnd(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled)
	{
		return 1;
	}
};

class CMainFrame : public CFrameWindowImpl<CMainFrame>, public CUpdateUI<CMainFrame>
{
	HUvcham		 m_hcam;
	CMainView	 m_view;
	UvchamDevice m_tdev, m_ti[UVCHAM_MAX];
	unsigned	 m_nFrameCount;
	DWORD		 m_dwTick;
	bool		 m_bRecord;
	BYTE*				m_pData;
	BITMAPINFOHEADER	m_header;

	BEGIN_MSG_MAP_EX(CMainFrame)
		MSG_WM_CREATE(OnCreate)
		MESSAGE_HANDLER(MSG_CALLBACK, OnMsgCallback)
		MESSAGE_HANDLER(WM_DESTROY, OnWmDestroy)
		MESSAGE_HANDLER(WM_TIMER, OnWmTimer)
		COMMAND_RANGE_HANDLER_EX(ID_DEVICE_DEVICE0, ID_DEVICE_DEVICEF, OnOpenDevice)
		COMMAND_ID_HANDLER_EX(ID_CONFIG_AUTOEXPOSURE, OnAutoExposure)
		COMMAND_ID_HANDLER_EX(ID_CONFIG_EXPOSURETIME, OnExposureTime)
		COMMAND_ID_HANDLER_EX(ID_ACTION_RECORD, OnRecord)
		CHAIN_MSG_MAP(CUpdateUI<CMainFrame>)
		CHAIN_MSG_MAP(CFrameWindowImpl<CMainFrame>)
	END_MSG_MAP()
	DECLARE_FRAME_WND_CLASS(NULL, IDR_MAIN);

	BEGIN_UPDATE_UI_MAP(CMainFrame)
		UPDATE_ELEMENT(ID_CONFIG_AUTOEXPOSURE, UPDUI_MENUPOPUP)
		UPDATE_ELEMENT(ID_CONFIG_EXPOSURETIME, UPDUI_MENUPOPUP)
		UPDATE_ELEMENT(ID_ACTION_RECORD, UPDUI_MENUPOPUP)
	END_UPDATE_UI_MAP()
public:
	CMainFrame()
	: m_hcam(NULL), m_nFrameCount(0), m_pData(NULL), m_view(this), m_dwTick(0), m_bRecord(false)
	{
		memset(&m_tdev, 0, sizeof(m_tdev));
		memset(m_ti, 0, sizeof(m_ti));
		memset(&m_header, 0, sizeof(m_header));

		m_header.biSize = sizeof(BITMAPINFOHEADER);
		m_header.biPlanes = 1;
		m_header.biBitCount = 24;
	}

	bool GetData(BITMAPINFOHEADER** pHeader, BYTE** pData)
	{
		if (m_pData)
		{
			*pData = m_pData;
			*pHeader = &m_header;
			return true;
		}

		return false;
	}
private:
	int OnCreate(LPCREATESTRUCT /*lpCreateStruct*/)
	{
		CMenuHandle menu = GetMenu();
		CMenuHandle submenu = menu.GetSubMenu(0);
		while (submenu.GetMenuItemCount() > 0)
			submenu.RemoveMenu(submenu.GetMenuItemCount() - 1, MF_BYPOSITION);

		const unsigned cnt = Uvcham_enum(m_ti);
		if (0 == cnt)
			submenu.AppendMenu(MF_GRAYED | MF_STRING, ID_DEVICE_DEVICE0, L"No Device");
		else
		{
			for (unsigned i = 0; i < cnt; ++i)
				submenu.AppendMenu(MF_STRING, ID_DEVICE_DEVICE0 + i, m_ti[i].displayname);
		}

		CreateSimpleStatusBar();
		{
			int iWidth[] = { 100, 400, -1 };
			CStatusBarCtrl statusbar(m_hWndStatusBar);
			statusbar.SetParts(_countof(iWidth), iWidth);
		}

		m_hWndClient = m_view.Create(m_hWnd, rcDefault, NULL, WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN, WS_EX_CLIENTEDGE);

		OnDeviceChanged();
		SetTimer(1, 1000, NULL);
		return 0;
	}

	void OnAutoExposure(UINT uNotifyCode, int nID, HWND wndCtl)
	{
		if (m_hcam)
		{
			int bAutoExposure = 0;
			if (SUCCEEDED(Uvcham_get(m_hcam, UVCHAM_AEXPO, &bAutoExposure)))
			{
				bAutoExposure = !bAutoExposure;
				Uvcham_put(m_hcam, UVCHAM_AEXPO, bAutoExposure);
				UISetCheck(ID_CONFIG_AUTOEXPOSURE, bAutoExposure ? 1 : 0);
				UIEnable(ID_CONFIG_EXPOSURETIME, !bAutoExposure);
			}
		}
	}

	void OnExposureTime(UINT uNotifyCode, int nID, HWND wndCtl)
	{
		if (m_hcam)
		{
			CExposureTimeDlg dlg(m_hcam);
			if (IDOK == dlg.DoModal())
				UpdateExposureTimeText();
		}
	}

	void OnRecord(UINT uNotifyCode, int nID, HWND wndCtl)
	{
		if (m_hcam)
		{
			if (m_bRecord)
			{
				UISetCheck(ID_ACTION_RECORD, 0);
				Uvcham_record(m_hcam, NULL); /* stop record */
			}
			else
			{
				CFileDialog dlg(FALSE);
				if (IDOK == dlg.DoModal())
				{
					CW2A w2a(dlg.m_szFileName);
					if (SUCCEEDED(Uvcham_record(m_hcam, w2a)))
					{
						m_bRecord = true;
						UISetCheck(ID_ACTION_RECORD, 1);
					}
				}
			}
		}
	}

	static void __stdcall CallbackFun(unsigned nEvent, void* pCallbackCtx)
	{
		CMainFrame* pthis = (CMainFrame*)pCallbackCtx;
		if (pthis)
			pthis->PostMessage(MSG_CALLBACK, nEvent);
	}

	void OnOpenDevice(UINT uNotifyCode, int nID, HWND wndCtl)
	{
		CloseDevice();

		m_nFrameCount = 0;
		m_dwTick = GetTickCount();
		m_hcam = Uvcham_open(m_ti[nID - ID_DEVICE_DEVICE0].id);
		if (m_hcam)
		{
			m_tdev = m_ti[nID - ID_DEVICE_DEVICE0];
			OnDeviceChanged();
			UpdateFrameText();

			int res = 0;
			Uvcham_get(m_hcam, UVCHAM_RES, &res);
			Uvcham_get(m_hcam, UVCHAM_WIDTH | res, (int*)&m_header.biWidth);
			Uvcham_get(m_hcam, UVCHAM_HEIGHT | res, (int*)&m_header.biHeight);
			m_header.biSizeImage = WIDTHBYTES(m_header.biWidth * m_header.biBitCount) * m_header.biHeight;
			m_pData = (BYTE*)malloc(m_header.biSizeImage);

			const HRESULT hr = Uvcham_start(m_hcam, NULL/* Pull Mode */, CallbackFun, this);
			if (SUCCEEDED(hr))
				OnDeviceChanged();
			else
			{
				CloseDevice();
				AtlMessageBoxHresult(m_hWnd, hr);
			}
		}
	}

	LRESULT OnWmTimer(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled)
	{
		if (1 == wParam)
		{
			if (m_hcam && (UIGetState(ID_CONFIG_AUTOEXPOSURE) & UPDUI_CHECKED))
				UpdateExposureTimeText();
		}
		return 0;
	}

	LRESULT OnWmDestroy(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled)
	{
		CloseDevice();
		CFrameWindowImpl<CMainFrame>::OnDestroy(uMsg, wParam, lParam, bHandled);
		return 0;
	}

	LRESULT OnMsgCallback(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled)
	{
		unsigned nEvent = (unsigned)wParam;
		if (nEvent & UVCHAM_EVENT_IMAGE)
		{
			if (SUCCEEDED(Uvcham_pull(m_hcam, m_pData))) /* Pull Mode */
			{
				++m_nFrameCount;
				UpdateFrameText();
				m_view.Invalidate();
			}
		}
		else if (nEvent & UVCHAM_EVENT_DISCONNECT)
			AtlMessageBox(m_hWnd, L"Camera disconnect.");
		else if (nEvent & UVCHAM_EVENT_ERROR)
			AtlMessageBox(m_hWnd, L"Generic error.");
		return 0;
	}

	void CloseDevice()
	{
		m_bRecord = false;
		if (m_hcam)
		{
			Uvcham_close(m_hcam);
			m_hcam = NULL;

			if (m_pData)
			{
				free(m_pData);
				m_pData = NULL;
			}
		}
		OnDeviceChanged();
	}

	void OnDeviceChanged()
	{
		CStatusBarCtrl statusbar(m_hWndStatusBar);

		if (NULL == m_hcam)
		{
			statusbar.SetText(0, L"");
			statusbar.SetText(1, L"");
			statusbar.SetText(2, L"");

			UISetCheck(ID_CONFIG_AUTOEXPOSURE, 0);
			UIEnable(ID_CONFIG_EXPOSURETIME, FALSE);
		}
		else
		{
			UpdateResolutionText();
			UpdateExposureTimeText();
			UpdateAE();
		}

		UIEnable(ID_CONFIG_AUTOEXPOSURE, m_hcam ? TRUE : FALSE);
		UIEnable(ID_ACTION_RECORD, m_hcam ? TRUE : FALSE);
		UISetCheck(ID_ACTION_RECORD, 0);
	}

	void UpdateAE()
	{
		if (m_hcam)
		{
			int bAutoExposure = 0;
			if (SUCCEEDED(Uvcham_get(m_hcam, UVCHAM_AEXPO, &bAutoExposure)))
			{
				UISetCheck(ID_CONFIG_AUTOEXPOSURE, bAutoExposure ? 1 : 0);
				UIEnable(ID_CONFIG_EXPOSURETIME, !bAutoExposure);
			}
		}
	}

	void UpdateResolutionText()
	{
		CStatusBarCtrl statusbar(m_hWndStatusBar);
		wchar_t res[128];
		int nWidth = 0, nHeight = 0;
		Uvcham_get(m_hcam, UVCHAM_WIDTH | 0, &nWidth);
		Uvcham_get(m_hcam, UVCHAM_HEIGHT | 0, &nHeight);
		swprintf(res, L"%u * %u", nWidth, nHeight);
		statusbar.SetText(0, res);
	}

	void UpdateFrameText()
	{
		CStatusBarCtrl statusbar(m_hWndStatusBar);
		wchar_t str[256];
		DWORD dw = GetTickCount();
		if (dw == m_dwTick)
			swprintf(str, L"%u", m_nFrameCount);
		else
			swprintf(str, L"%u, %.1f", m_nFrameCount, m_nFrameCount * 1000.0 / (dw - m_dwTick));
		statusbar.SetText(2, str);
	}

	void UpdateExposureTimeText()
	{
		if (m_hcam)
		{
			CStatusBarCtrl statusbar(m_hWndStatusBar);
			wchar_t res[128];
			int nTime = 0, Gain = 0;
			if (SUCCEEDED(Uvcham_get(m_hcam, UVCHAM_EXPOTIME, &nTime)) && SUCCEEDED(Uvcham_get(m_hcam, UVCHAM_AGAIN, &Gain)))
			{
				swprintf(res, L"ExposureTime = %d, Gain = %d", nTime, Gain);
				statusbar.SetText(1, res);
			}
		}
	}
};

LRESULT CMainView::OnWmPaint(UINT uMsg, WPARAM wParam, LPARAM lParam, BOOL& bHandled)
{
	CPaintDC dc(m_hWnd);

	RECT rc;
	GetClientRect(&rc);
	BITMAPINFOHEADER* pHeader = NULL;
	BYTE* pData = NULL;
	if (m_pMainFrame->GetData(&pHeader, &pData))
	{
		const int m = dc.SetStretchBltMode(COLORONCOLOR);
		StretchDIBits(dc, rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top, 0, 0, pHeader->biWidth, pHeader->biHeight, pData, (BITMAPINFO*)pHeader, DIB_RGB_COLORS, SRCCOPY);
		dc.SetStretchBltMode(m);
	}
	else
	{
		dc.FillRect(&rc, (HBRUSH)WHITE_BRUSH);
	}

	return 0;
}

static int Run(int nCmdShow = SW_SHOWDEFAULT)
{
	CMessageLoop theLoop;
	_Module.AddMessageLoop(&theLoop);

	CMainFrame frmMain;
	if (frmMain.CreateEx() == NULL)
	{
		ATLTRACE(_T("Main window creation failed!\n"));
		return 0;
	}
	frmMain.ShowWindow(nCmdShow);

	int nRet = theLoop.Run();

	_Module.RemoveMessageLoop();
	return nRet;
}

int WINAPI _tWinMain(HINSTANCE hInstance, HINSTANCE /*hPrevInstance*/, LPTSTR /*pCmdLine*/, int nCmdShow)
{
	INITCOMMONCONTROLSEX iccx;
	iccx.dwSize = sizeof(iccx);
	iccx.dwICC = ICC_COOL_CLASSES | ICC_BAR_CLASSES;
	InitCommonControlsEx(&iccx);

	OleInitialize(NULL);

	_Module.Init(NULL, hInstance);
	int nRet = Run(nCmdShow);
	_Module.Term();
	return nRet;
}