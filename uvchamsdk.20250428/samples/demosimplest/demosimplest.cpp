#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <amvideo.h>
#include "uvcham.h"

HUvcham g_hcam = NULL;
void* g_pImageData = NULL;
unsigned g_total = 0;

static void __stdcall CallbackFun(unsigned nEvent, void* /*pCallbackCtx*/)
{
    if (nEvent & UVCHAM_EVENT_IMAGE)
	{
        if (SUCCEEDED(Uvcham_pull(g_hcam, g_pImageData))) /* Pull Mode */
            wprintf(L"pull image ok, total = %u\n", ++g_total);
        else
            wprintf(L"pull image failed\n");
	}
    if (nEvent & UVCHAM_EVENT_ERROR)
        wprintf(L"error\n");
    if (nEvent & UVCHAM_EVENT_DISCONNECT)
        wprintf(L"disconnect\n");
}

int main(int, char**)
{
    CoInitialize(nullptr);

    UvchamDevice arr[UVCHAM_MAX];
    int n = Uvcham_enum(arr);
    if (n <= 0)
    {
        wprintf(L"no camera found\n");
        return -1;
    }
    for (int i = 0; i < n; ++i)
        wprintf(L"%d: %s\n", i + 1, arr[i].displayname);
    g_hcam = Uvcham_open(arr[0].id);
    if (g_hcam)
        wprintf(L"open %s ok\n", arr[0].displayname);
    else
    {
        wprintf(L"open %s failed\n", arr[0].displayname);
        return -1;
    }
    int resnum = 0, w = 0, h = 0;
    Uvcham_range(g_hcam, UVCHAM_RES, nullptr, &resnum, nullptr);
    for (int i = 0; i < resnum; ++i)
    {
        Uvcham_get(g_hcam, UVCHAM_WIDTH | i, &w);
        Uvcham_get(g_hcam, UVCHAM_HEIGHT | i, &h);
        wprintf(L"%d: %d * %d\n", i + 1, w, h);
    }

    Uvcham_get(g_hcam, UVCHAM_WIDTH | 0, &w);
    Uvcham_get(g_hcam, UVCHAM_HEIGHT | 0, &h);

    g_pImageData = malloc(WIDTHBYTES(w * 24) * h);
    if (NULL == g_pImageData)
        printf("failed to malloc\n");
    else
    {
        HRESULT hr = Uvcham_start(g_hcam, NULL/* Pull Mode */, CallbackFun, nullptr);
        if (FAILED(hr))
            wprintf(L"failed to start camera, hr = %08x\n", hr);
        else
        {
            wprintf(L"press ENTER to exit\n");
            getc(stdin);
        }
    }
    
    /* cleanup */
    Uvcham_close(g_hcam);
    if (g_pImageData)
        free(g_pImageData);
    return 0;
}
