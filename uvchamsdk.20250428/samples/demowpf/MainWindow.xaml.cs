using System;
using System.IO;
using System.Windows.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Runtime.InteropServices;

namespace demowpf
{
    public partial class MainWindow : Window
    {
        private Uvcham cam_ = null;
        private WriteableBitmap bmp_ = null;
        private DispatcherTimer timer_ = null;
        private bool started_ = false;
        private uint count_ = 0;

        public MainWindow()
        {
            InitializeComponent();

            snap_.IsEnabled = false;
            auto_exposure_.IsEnabled = false;
            white_balance_.IsEnabled = false;
            slider_expotime_.IsEnabled = false;
            slider_r_.IsEnabled = false;
            slider_g_.IsEnabled = false;
            slider_b_.IsEnabled = false;

            Closing += (sender, e) =>
            {
                cam_?.close();
                cam_ = null;
            };
        }

        private void OnEventError()
        {
            cam_.close();
            cam_ = null;
            MessageBox.Show("Generic error.");
        }

        private void OnEventDisconnect()
        {
            cam_.close();
            cam_ = null;
            MessageBox.Show("Camera disconnect.");
        }

        private void UpdateExpoTime()
        {
            int val = 0;
            cam_.get(Uvcham.eCMD.EXPOTIME, out val);
            slider_expotime_.Value = val;
            label_expotime_.Content = val.ToString();
        }

        private void UpdateAwb()
        {
            int val = 0;
            cam_.get(Uvcham.eCMD.WBRED, out val);
            slider_r_.Value = val;
            label_r_.Content = val.ToString();
            cam_.get(Uvcham.eCMD.WBGREEN, out val);
            slider_g_.Value = val;
            label_g_.Content = val.ToString();
            cam_.get(Uvcham.eCMD.WBBLUE, out val);
            slider_b_.Value = val;
            label_b_.Content = val.ToString();
        }

        private void OnEventImage()
        {
            if (bmp_ != null)
            {
                try
                {
                    bmp_.Lock();
                    try
                    {
                        cam_.pull(bmp_.BackBuffer);/* Pull Mode */
                        bmp_.AddDirtyRect(new Int32Rect(0, 0, bmp_.PixelWidth, bmp_.PixelHeight));
                    }
                    finally
                    {
                        bmp_.Unlock();
                    }
                    image_.Source = bmp_;
                }
                catch (Exception ex)
                {
                    MessageBox.Show(ex.ToString());
                }
            }
        }

        private void startDevice(string id)
        {
            cam_ = Uvcham.open(id);
            if (cam_ != null)
            {
                
                auto_exposure_.IsEnabled = true;
                snap_.IsEnabled = true;
                white_balance_.IsEnabled = true;

                int width = 0, height = 0, res = 0;
                cam_.get(Uvcham.eCMD.RES, out res);
                cam_.get(Uvcham.eCMD.WIDTH | ((Uvcham.eCMD)res), out width);
                cam_.get(Uvcham.eCMD.HEIGHT | ((Uvcham.eCMD)res), out height);
                if ((width > 0) && (height > 0))
                {
                    cam_.put(Uvcham.eCMD.FORMAT, 1); //BRGA8888
                    /* The backend of WPF is Direct3D/Direct2D, which is different from Winform's backend GDI.
                     * We use their respective native formats, Bgr32 in WPF, and Bgr24 in Winform
                     */
                    bmp_ = new WriteableBitmap(width, height, 0, 0, PixelFormats.Bgr32, null);
                    if (cam_.start(IntPtr.Zero/* Pull Mode */, (nEvent) =>
                    {
                        /* this is called by internal thread of uvcham.dll which is NOT the same of UI thread.
                         * So we use BeginInvoke
                         */
                        Dispatcher.BeginInvoke((Action)(() =>
                        {
                            /* this run in the UI thread */
                            if (cam_ != null)
                            {
                                if ((nEvent & Uvcham.eEVENT.IMAGE) != 0)
                                    OnEventImage();
                                else if ((nEvent & Uvcham.eEVENT.ERROR) != 0)
                                    OnEventError();
                                else if ((nEvent & Uvcham.eEVENT.DISCONNECT) != 0)
                                    OnEventDisconnect();
                            }
                        }));
                    }) < 0)
                        MessageBox.Show("Failed to start camera.");
                    else
                    {
                        int nmin, nmax, ndef;
                        cam_.range(Uvcham.eCMD.EXPOTIME, out nmin, out nmax, out ndef);
                        slider_expotime_.Minimum = nmin;
                        slider_expotime_.Maximum = nmax;
                        cam_.range(Uvcham.eCMD.WBRED, out nmin, out nmax, out ndef);
                        slider_r_.Minimum = nmin;
                        slider_r_.Maximum = nmax;
                        cam_.range(Uvcham.eCMD.WBGREEN, out nmin, out nmax, out ndef);
                        slider_g_.Minimum = nmin;
                        slider_g_.Maximum = nmax;
                        cam_.range(Uvcham.eCMD.WBBLUE, out nmin, out nmax, out ndef);
                        slider_b_.Minimum = nmin;
                        slider_b_.Maximum = nmax;

                        UpdateExpoTime();
                        UpdateAwb();
                        int val = 0;
                        cam_.get(Uvcham.eCMD.AEXPO, out val);
                        auto_exposure_.IsChecked = (1 == val);
                        slider_expotime_.IsEnabled = (1 != val);
                        cam_.get(Uvcham.eCMD.WBMODE, out val);
                        auto_exposure_.IsChecked = (1 == val);
                        slider_r_.IsEnabled = (1 != val);
                        slider_g_.IsEnabled = (1 != val);
                        slider_b_.IsEnabled = (1 != val);

                        timer_ = new DispatcherTimer() { Interval = new TimeSpan(0, 0, 1) };
                        timer_.Tick += (object sender, EventArgs e) =>
                        {
                            if (cam_ != null)
                            {
                                if (auto_exposure_.IsChecked ?? false)
                                    UpdateExpoTime();
                                if (white_balance_.IsChecked ?? false)
                                    UpdateAwb();
                            }
                        };
                        timer_.Start();
                    }

                    started_ = true;
                }
            }
        }

        private void onClick_start(object sender, RoutedEventArgs e)
        {
            if (cam_ != null)
                return;

            Uvcham.Device[] arr = Uvcham.Enum();
            if (arr.Length <= 0)
                MessageBox.Show("No camera found.");
            else if (1 == arr.Length)
                startDevice(arr[0].id);
            else
            {
                ContextMenu menu = new ContextMenu() { PlacementTarget = start_, Placement = PlacementMode.Bottom };
                for (int i = 0; i < arr.Length; ++i)
                {
                    MenuItem mitem = new MenuItem() { Header = arr[i].displayname, CommandParameter = i }; //inbox
                    mitem.Click += (nsender, ne) =>
                    {
                        int idx = (int)(((MenuItem)nsender).CommandParameter); //oubox
                        if ((idx >= 0) && (idx < arr.Length))
                            startDevice(arr[idx].id);
                    };
                    menu.Items.Add(mitem);
                }
                menu.IsOpen = true;
            }
        }

        private void onClick_whitebalance(object sender, RoutedEventArgs e)
        {
            if (started_)
            {
                cam_?.put(Uvcham.eCMD.WBMODE, (white_balance_.IsChecked ?? false) ? 1 : 0);
                slider_r_.IsEnabled = !(white_balance_.IsChecked ?? false);
                slider_g_.IsEnabled = !(white_balance_.IsChecked ?? false);
                slider_b_.IsEnabled = !(white_balance_.IsChecked ?? false);
            }
        }

        private void onChanged_r(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if ((cam_ != null) && started_)
            {
                cam_.put(Uvcham.eCMD.WBRED, (int)slider_r_.Value);
                label_r_.Content = ((int)slider_r_.Value).ToString();
            }
        }

        private void onChanged_g(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if ((cam_ != null) && started_)
            {
                cam_.put(Uvcham.eCMD.WBGREEN, (int)slider_g_.Value);
                label_g_.Content = ((int)slider_g_.Value).ToString();
            }
        }

        private void onChanged_b(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if ((cam_ != null) && started_)
            {
                cam_.put(Uvcham.eCMD.WBBLUE, (int)slider_b_.Value);
                label_b_.Content = ((int)slider_b_.Value).ToString();
            }
        }

        private void onChanged_expotime(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if ((cam_ != null) && started_)
            {
                cam_.put(Uvcham.eCMD.EXPOTIME, (int)slider_expotime_.Value);
                label_expotime_.Content = ((int)slider_expotime_.Value).ToString();
            }
        }

        private void onClick_auto_exposure(object sender, RoutedEventArgs e)
        {
            if (started_)
            {
                cam_?.put(Uvcham.eCMD.AEXPO, (auto_exposure_.IsChecked ?? false) ? 1 : 0);
                slider_expotime_.IsEnabled = !(auto_exposure_.IsChecked ?? false);
            }
        }

        private void OnClick_snap(object sender, RoutedEventArgs e)
        {
            if ((cam_ != null) && (bmp_ != null))
            {
                using (FileStream fileStream = new FileStream(string.Format("demowpf_{0}.bmp", ++count_), FileMode.Create))
                {
                    BitmapEncoder encoder = new BmpBitmapEncoder();
                    encoder.Frames.Add(BitmapFrame.Create(bmp_));
                    encoder.Save(fileStream);
                }
            }
        }
    }
}
