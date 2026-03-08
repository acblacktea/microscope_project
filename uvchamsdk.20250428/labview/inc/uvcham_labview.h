#ifndef __uvcham_labview_h__
#define __uvcham_labview_h__

#include "extcode.h"

#ifdef UVCHAM_LABVIEW_EXPORTS
#define UVCHAM_LABVIEW_API(x) __declspec(dllexport)    x   __cdecl
#else
#define UVCHAM_LABVIEW_API(x) __declspec(dllimport)    x   __cdecl
#include "uvcham.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

UVCHAM_LABVIEW_API(HRESULT) Start(HUvcham h, void* pFrameBuffer, LVUserEventRef* rwer);

#ifdef __cplusplus
}
#endif

#endif