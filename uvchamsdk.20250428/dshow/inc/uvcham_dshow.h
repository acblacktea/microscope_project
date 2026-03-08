#ifndef __uvcham_dshow_h__
#define __uvcham_dshow_h__

/* Version: 1.28395.20250428 */
/* Both the DirectShow source filter and the output pin(s) support this interface.
    That is to say, you can use QueryInterface on the filter or the pin(s) to get the IToupcam interface.
*/
// {2FD6EEB6-D109-4393-BA9D-BD4869BC82CC}
DEFINE_GUID(IID_IUvcham, 0x2fd6eeb6, 0xd109, 0x4393, 0xba, 0x9d, 0xbd, 0x48, 0x69, 0xbc, 0x82, 0xcc);

DECLARE_INTERFACE_(IUvcham, IUnknown)
{
    STDMETHOD(put) (THIS_ long type, long value) PURE;
    STDMETHOD(get) (THIS_ long type, long* value) PURE;
    STDMETHOD(range) (THIS_ long type, long* lmin, long* lmax, long* ldef) PURE;
};

#endif
