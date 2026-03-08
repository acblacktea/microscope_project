using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Security.Permissions;
using System.Runtime.ConstrainedExecution;
using System.Collections.Generic;
using System.Threading;

/*
    Version: @VERM@.$WCREV$.@WCNOW@
    For Microsoft dotNET Framework & dotNet Core
    We use P/Invoke to call into the uvcham.dll API, the c# class Uvcham is a thin wrapper class to the native api of uvcham.dll
*/
internal class Uvcham : IDisposable
{
    public enum eEVENT : uint
    {
        IMAGE         = 0x0001,
        DISCONNECT    = 0x0002,    /* camera disconnect */
        ERROR         = 0x0004     /* error */
    };
    
    /* command: get & put */
    public enum eCMD : uint
    {
        FLIPHORZ            = 0x00000002,    /* flip horizontal */
        FLIPVERT            = 0x00000003,    /* flip vertical */
        AEXPOTARGET         = 0x00000004,    /* exposure compensation */
        DENOISE             = 0x00000005,    /* denoise */
        WBROILEFT           = 0x00000006,    /* white balance mode roi: left */
        WBROIWIDTH          = 0x00000007,    /* white balance mode roi: width, width >= UVCHAM_WBROI_WIDTH_MIN */
        WBROITOP            = 0x00000008,    /* white balance mode roi: top */
        WBROIHEIGHT         = 0x0000000a,    /* white balance mode roi: height, height >= UVCHAM_WBROI_HEIGHT_MIN */
        YEAR                = 0x0000000b,    /* firmware version: year */
        MONTH               = 0x0000000c,    /* firmware version: month */
        DAY                 = 0x0000000d,    /* firmware version: day */
        WBMODE              = 0x00000010,    /* white balance mode: 0 = manual, 1 = auto, 2 = roi */
        EXPOTIME            = 0x00000011,    /* exposure time */
        AEXPO               = 0x00000013,    /* auto exposure: 0 = manual, 1 = auto */
        SHARPNESS           = 0x00000016,
        SATURATION          = 0x00000017,
        GAMMA               = 0x00000018,
        CONTRAST            = 0x00000019,
        BRIGHTNESS          = 0x0000001a,
        HZ                  = 0x0000001b,    /* 0 -> 60HZ AC;  1 -> 50Hz AC;  2 -> DC */
        WBRED               = 0x0000001c,    /* white balance: R/G/B gain */
        WBGREEN             = 0x0000001d,    /* white balance: R/G/B gain */
        WBBLUE              = 0x0000001e,    /* white balance: R/G/B gain */
        HUE                 = 0x0000001f,
        CHROME              = 0x00000020,    /* color(0)/grey(1) */
        AFPOSITION          = 0x00000021,    /* af (auto focus) sensor board positon, now is 0~854 */
        AFMODE              = 0x00000022,    /* af mode (0:manul focus; 1:auto focus; 2:once focus; 3:Conjugate calibration) */
        AFZONE              = 0x00000023,    /* af zone: Bytes[0]=ROW; Bytes[1]=COLUMN  */
        AFFEEDBACK          = 0x00000024,    /* auto focus information feedback
                                                    0: unknown
                                                    1: focused
                                                    2: focusing
                                                    3: defocuse (out of focus)
                                                    4: up (workbench move up)
                                                    5: down (workbench move down)
                                             */
        AFPOSITION_ABSOLUTE = 0x00000025,    /* absolute af sensor board positon: -5400um~10600um(-5.4mm~10.6mm) */
        PAUSE               = 0x00000026,    /* pause */
        SN                  = 0x00000027,    /* serial number */
        BPS                 = 0x00000032,    /* bitrate: Mbps */
        LIGHT_ADJUSTMENT    = 0x00000033,    /* light source brightness adjustment */
        ZOOM                = 0x00000034,    /* SET only */
        USER                = 0x00000035,    /* User */
        EF_MODE             = 0x00000036,
        EF_FL               = 0x00000037,
        EF_APERTURE_MIN_MAX = 0x00000038,
        EF_APERTURE_CUR     = 0x00000039,
        EF_FOCUS_CUR        = 0x0000003a,
        EF_FOCUS_MAX        = 0x0000003b,
        EF_LENS_ID          = 0x0000003c,
        EF_AFMF             = 0x0000003d,
        EF_WD_ENABLE        = 0x0000003e,
        EF_WD_NEAR          = 0x0000003f,
        EF_WD_FAR           = 0x00000040,
        TEMP                = 0x00000042,    /* temp/tint mode: color temperature */
        TINT                = 0x00000043,    /* temp/tint mode: tint */
        AGAIN               = 0x00000084,    /* analog gain */
        NEGATIVE            = 0x00000085,    /* negative film */
        REALTIME            = 0x00000086,    /* realtime: 1 => ON, 0 => OFF */
        FORMAT              = 0x000000fe,    /* output format: 0 => BGR888, 1 => BGRA8888, 2 => RGB888, 3 => RGBA8888; default: 0
                                                Can be changed only when camera is not running.
                                             */
        UVCHAM_CODEC        = 0x01000000,    /* codec:
                                                    Can be changed only when camera is not running.
                                                    To get the number of the supported codec, use: Uvcham_range(h, UVCHAM_CODEC, nullptr, &num, nullptr)
                                             */
        CODEC_FOURCC        = 0x02000000,    /* to get fourcc of the nth codec, use: Uvcham_get(h, UVCHAM_CODEC_FOURCC | n, &fourcc), such as MAKEFOURCC('M', 'J', 'P', 'G') */
        RES                 = 0x10000000,    /* resolution:
                                                    Can be changed only when camera is not running.
                                                    To get the number of the supported resolution, use: Uvcham_range(h, UVCHAM_RES, nullptr, &num, nullptr)
                                             */
        WIDTH               = 0x40000000,    /* to get the nth width, use: Uvcham_get(h, UVCHAM_WIDTH | n, &width) */
        HEIGHT              = 0x80000000
    };
    /********************************************************************/
    /* How to enum the resolutions:                                     */
    /*     cam_.range(eCMD.RES, null, out num, null);                   */
    /*     for (int i = 0; i <= num; ++i)                               */
    /*     {                                                            */
    /*         int width = 0, height = 0;                               */
    /*         cam_.get(eCMD.WIDTH | i, out width);                     */
    /*         cam_.get(eCMD.HEIGHT | i, out height);                   */
    /*         Console.WriteLine("%d: %d x %d", i, width, height);      */
    /*     }                                                            */
    /********************************************************************/

    /********************************************************************/
    /* "Direct Mode" vs "Pull Mode"                                     */
    /* (1) Direct Mode:                                                 */
    /*     (a) cam_.start(h, pFrameBuffer, ...)                         */
    /*     (b) pros: simple, slightly more efficient                    */
    /* (2) Pull Mode:                                                   */
    /*     (a) cam_.start(h, null, ...)                                 */
    /*     (b) use cam_.pull(h, pFrameBuffer) to pull image             */
    /*     (c) pros: never frame confusion                              */
    /********************************************************************/

    /********************************************************************/
    /* How to test whether the camera supports auto focus:              */
    /*     if (SUCCEEDED(cam_.get(UVCHAM_AFZONE, out val))              */
    /*         // yes, it supports                                      */
    /*     else                                                         */
    /*         // not supported                                         */
    /********************************************************************/
    public const int WBROI_WIDTH_MIN   = 48;
    public const int WBROI_HEIGHT_MIN  = 32;

    public struct Device
    {
        public string displayname; /* display name */
        public string id;          /* unique and opaque id of a connected camera */
    };

    /* only for compatibility with .Net 4.0 and below */
    public static IntPtr IncIntPtr(IntPtr p, int offset)
    {
        return new IntPtr(p.ToInt64() + offset);
    }

    public delegate void DelegateCALLBACK(eEVENT nEvent);

    [DllImport("ntdll.dll", ExactSpelling = true, CallingConvention = CallingConvention.Cdecl, SetLastError = false)]
    public static extern void memcpy(IntPtr dest, IntPtr src, IntPtr count);

    static public int TDIBWIDTHBYTES(int bits)
    {
        return ((bits + 31) & (~31)) / 8;
    }

    /* get the version of this dll, which is: @VERM@.$WCREV$.@WCNOW@ */
    public static string version()
    {
        return Uvcham_version();
    }

    public void close()
    {
        Dispose();
    }

    /* enumerate the cameras that are currently connected to computer */
    public static Device[] Enum()
    {
        IntPtr p = Marshal.AllocHGlobal(512 * 16);
        IntPtr ti = p;
        uint cnt = Uvcham_enum(p);
        Device[] arr = new Device[cnt];
        for (uint i = 0; i < cnt; ++i)
        {
            arr[i].displayname = Marshal.PtrToStringUni(p);
            p = IncIntPtr(p, sizeof(char) * 128);
            arr[i].id = Marshal.PtrToStringUni(p);
            p = IncIntPtr(p, sizeof(char) * 128);
        }
        Marshal.FreeHGlobal(ti);
        return arr;
    }

    /*
        the object of Uvcham must be obtained by static mothod open, it cannot be obtained by obj = new Uvcham (The constructor is private on purpose)
    */
    public static Uvcham open(string camId)
    {
        SafeCamHandle h = Uvcham_open(camId);
        if (h == null || h.IsInvalid || h.IsClosed)
            return null;
        return new Uvcham(h);
    }

    public int start(IntPtr pFrameBuffer, DelegateCALLBACK dCallback)
    {
        dCallback_ = dCallback;
        pCallback_ = delegate (eEVENT nEvent, IntPtr pCtx)
        {
            Uvcham pthis = null;
            if (map_.TryGetValue(pCtx.ToInt32(), out pthis) && (pthis != null))
            {
                if (pthis.dCallback_ != null)
                    pthis.dCallback_(nEvent);
            }
        };
        return Uvcham_start(handle_, pFrameBuffer, pCallback_, id_);
    }

    public int stop()
    {
        return Uvcham_stop(handle_);
    }

    public int pull(IntPtr pFrameBuffer)
    {
        return Uvcham_pull(handle_, pFrameBuffer);
    }
    
    /* filePath == null means to stop record.
        support file extension: *.asf, *.mp4, *.mkv
    */
    public int record(string filePath)
    {
        return Uvcham_record(handle_, filePath);
    }

    public int put(eCMD nId, int val)
    {
        return Uvcham_put(handle_, nId, val);
    }

    public int get(eCMD nId, out int pVal)
    {
        return Uvcham_get(handle_, nId, out pVal);
    }

    public int range(eCMD nId, out int pMin, out int pMax, out int pDef)
    {
        return Uvcham_range(handle_, nId, out pMin, out pMax, out pDef);
    }

    private static int sid_ = 0;
    private static Dictionary<int, Uvcham> map_ = new Dictionary<int, Uvcham>();

    private SafeCamHandle handle_;
    private IntPtr id_;
    private DelegateCALLBACK dCallback_;
    private CALLBACK pCallback_;

    /*
        the object of Uvcham must be obtained by static mothod open, it cannot be obtained by obj = new Uvcham (The constructor is private on purpose)
    */
    private Uvcham(SafeCamHandle h)
    {
        handle_ = h;
        id_ = new IntPtr(Interlocked.Increment(ref sid_));
        map_.Add(id_.ToInt32(), this);
    }

    ~Uvcham()
    {
        Dispose(false);
    }

    [SecurityPermission(SecurityAction.Demand, UnmanagedCode = true)]
    protected virtual void Dispose(bool disposing)
    {
        // Note there are three interesting states here:
        // 1) CreateFile failed, _handle contains an invalid handle
        // 2) We called Dispose already, _handle is closed.
        // 3) _handle is null, due to an async exception before
        //    calling CreateFile. Note that the finalizer runs
        //    if the constructor fails.
        if (handle_ != null && !handle_.IsInvalid)
        {
            // Free the handle
            handle_.Dispose();
        }
        // SafeHandle records the fact that we've called Dispose.
    }

    public void Dispose()  // Follow the Dispose pattern - public nonvirtual.
    {
        Dispose(true);
        map_.Remove(id_.ToInt32());
        GC.SuppressFinalize(this);
    }

    private class SafeCamHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        private static extern void Uvcham_close(IntPtr h);

        public SafeCamHandle()
            : base(true)
        {
        }

        [ReliabilityContract(Consistency.WillNotCorruptState, Cer.MayFail)]
        override protected bool ReleaseHandle()
        {
            // Here, we must obey all rules for constrained execution regions.
            Uvcham_close(handle);
            return true;
        }
    };

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate void CALLBACK(eEVENT nEvent, IntPtr pCtx);

    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    [return: MarshalAs(UnmanagedType.LPWStr)]
    private static extern string Uvcham_version();
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern uint Uvcham_enum(IntPtr ti);
    /* camId == null means to open the first device */
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern SafeCamHandle Uvcham_open([MarshalAs(UnmanagedType.LPWStr)] string camId);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_start(SafeCamHandle h, IntPtr pFrameBuffer, CALLBACK pCallbackFun, IntPtr pCallbackCtx);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_stop(SafeCamHandle h);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_put(SafeCamHandle h, eCMD nId, int val);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_get(SafeCamHandle h, eCMD nId, out int pVal);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_range(SafeCamHandle h, eCMD nId, out int pMin, out int pMax, out int pDef);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_pull(SafeCamHandle h, IntPtr pFrameBuffer);
    [DllImport("uvcham.dll", ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    private static extern int Uvcham_record(SafeCamHandle h, [MarshalAs(UnmanagedType.LPStr)] string filePath);
}
