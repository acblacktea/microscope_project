using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace demowinform
{
    public partial class Form1 : Form
    {
        private Uvcham cam_ = null;
        private Bitmap bmp_ = null;
        private int width_ = 0, height_ = 0;
        private int count_ = 0;
        private Timer timer_ = null;

        public Form1()
        {
            InitializeComponent();
            pictureBox1.Width = ClientRectangle.Right - pictureBox1.Left - button1.Top;
            pictureBox1.Height = ClientRectangle.Height - 2 * button1.Top;

            timer_ = new Timer() { Interval = 1000, Enabled = true };
            timer_.Tick += (source, e) => UpdateExpoTime();
        }

        private void Form_SizeChanged(object sender, EventArgs e)
        {
            pictureBox1.Width = ClientRectangle.Right - pictureBox1.Left - button1.Top;
            pictureBox1.Height = ClientRectangle.Height - 2 * button1.Top;
        }

        private void Form1_Load(object sender, EventArgs e)
        {
            button3.Enabled = trackBar1.Enabled = checkBox1.Enabled = false;
        }

        private void UpdateExpoTime()
        {
            if (cam_ != null)
            {
                int val = 0;
                cam_.get(Uvcham.eCMD.EXPOTIME, out val);
                trackBar1.Value = val;
                label1.Text = val.ToString();
            }
        }

        private void OnStart(object sender, EventArgs e)
        {
            if (cam_ != null)
                return;

            Uvcham.Device[] arr = Uvcham.Enum();
            if (arr.Length <= 0)
                MessageBox.Show("No camera found.");
            else
            {
                cam_ = Uvcham.open(arr[0].id);
                if (cam_ != null)
                {
                    cam_.put(Uvcham.eCMD.WBMODE, 2);

                    checkBox1.Enabled = trackBar1.Enabled = true;
                    button3.Enabled = true;

                    cam_.get(Uvcham.eCMD.WIDTH | 0, out width_);
                    cam_.get(Uvcham.eCMD.HEIGHT | 0, out height_);
                    cam_.put(Uvcham.eCMD.FLIPVERT, 1);
                    bmp_ = new Bitmap(width_, height_, PixelFormat.Format24bppRgb);
                    if (cam_.start(IntPtr.Zero/* Pull Mode */, (nEvent) =>
                    {
                        /* this is called by internal thread of uvcham.dll which is NOT the same of UI thread.
                         * Why we use BeginInvoke, Please see:
                         * http://msdn.microsoft.com/en-us/magazine/cc300429.aspx
                         * http://msdn.microsoft.com/en-us/magazine/cc188732.aspx
                         * http://stackoverflow.com/questions/1364116/avoiding-the-woes-of-invoke-begininvoke-in-cross-thread-winform-event-handling
                         */
                        BeginInvoke((Action)(() =>
                        {
                            /* this run in the UI thread */
                            if (cam_ != null)
                            {
                                if (0 != (nEvent & Uvcham.eEVENT.DISCONNECT))
                                {
                                    cam_.close();
                                    MessageBox.Show("Camera disconnect.");
                                }
                                else if (0 != (nEvent & Uvcham.eEVENT.ERROR))
                                {
                                    cam_.close();
                                    MessageBox.Show("Generic error.");
                                }
                                else if (0 != (nEvent & Uvcham.eEVENT.IMAGE))
                                {
                                    if (bmp_ != null)
                                    {
                                        try
                                        {
                                            BitmapData bmpdata = bmp_.LockBits(new Rectangle(0, 0, bmp_.Width, bmp_.Height), ImageLockMode.WriteOnly, bmp_.PixelFormat);
                                            if (bmpdata.Scan0 != IntPtr.Zero)
                                            {
                                                cam_.pull(bmpdata.Scan0);/* Pull Mode */
                                                bmp_.UnlockBits(bmpdata);
                                                pictureBox1.Image = bmp_;
                                            }
                                        }
                                        catch (Exception ex)
                                        {
                                            MessageBox.Show(ex.ToString());
                                        }
                                    }
                                }
                            }
                        }));
                    }) < 0)
                        MessageBox.Show("Failed to start camera.");
                    else
                    {
                        int nMin = 0, nMax = 0, nDef = 0;
                        cam_.range(Uvcham.eCMD.EXPOTIME, out nMin, out nMax, out nDef);
                        trackBar1.SetRange(nMin, nMax);

                        UpdateExpoTime();
                        int val = 0;
                        cam_.get(Uvcham.eCMD.AEXPO, out val);
                        checkBox1.Checked = (val != 0);
                        trackBar1.Enabled = (val == 0);
                    }
                }
            }
        }

        private void OnClosing(object sender, FormClosingEventArgs e)
        {
            cam_?.close();
			cam_ = null;
        }

        private void checkBox1_CheckedChanged(object sender, EventArgs e)
        {
            cam_?.put(Uvcham.eCMD.AEXPO, checkBox1.Checked ? 1 : 0);
            trackBar1.Enabled = !checkBox1.Checked;
        }

        private void OnExpoValueChange(object sender, EventArgs e)
        {
            if ((!checkBox1.Checked) && (cam_ != null))
            {
                cam_?.put(Uvcham.eCMD.EXPOTIME, trackBar1.Value);
                label1.Text = trackBar1.Value.ToString();
            }
        }

        private void onSnap(object sender, EventArgs e)
        {
            if ((cam_ != null) && (bmp_ != null))
                bmp_.Save(string.Format("demowinform_{0}.jpg", ++count_), ImageFormat.Jpeg);
        }

        private void OnWhiteBalanceOnce(object sender, EventArgs e)
        {
            cam_?.put(Uvcham.eCMD.WBMODE, 3);
        }
    }
}
