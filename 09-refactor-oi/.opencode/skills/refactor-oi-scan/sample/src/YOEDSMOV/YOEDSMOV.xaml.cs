using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Windows;
using System.Windows.Controls;
using System.Web;

using YOEDSMOV.Common;

namespace YOEDSMOV
{
    /// <summary>
    /// EDS 반출 화면. Lot 을 선택해 반출 확정을 겁니다.
    /// </summary>
    public partial class YOEDSMOV : UserControl, INotifyPropertyChanged
    {
        private readonly SqlManager _sqlManager = new SqlManager("YOEDSMOV");
        private readonly RuleManager _ruleManager = new RuleManager("YOEDSMOV");

        private string _appName = "YOEDSMOV";
        private string _lineId = string.Empty;
        private string _operId = string.Empty;
        private bool _isFirstLoaded = false;

        private int MaxRowCount = 1000;

        private string _lotStatus = string.Empty;
        private string _statusMessage = string.Empty;
        private double _rowHeight = 24;

        public event PropertyChangedEventHandler PropertyChanged;

        public string LotStatus
        {
            get { return _lotStatus; }
            set { _lotStatus = value; OnPropertyChanged("LotStatus"); }
        }

        public string StatusMessage
        {
            get { return _statusMessage; }
            set { _statusMessage = value; OnPropertyChanged("StatusMessage"); }
        }

        public double RowHeight
        {
            get { return _rowHeight; }
            set { _rowHeight = value; OnPropertyChanged("RowHeight"); }
        }

        public YOEDSMOV()
        {
            InitializeComponent();
            InitGridColumns();
        }

        private void OnPropertyChanged(string name)
        {
            if (PropertyChanged != null)
            {
                PropertyChanged(this, new PropertyChangedEventArgs(name));
            }
        }

        private void InitGridColumns()
        {
            grdLot.Columns.Clear();
            grdLot.AddTextColumn("LOT_ID", "Lot ID", 140);
            grdLot.AddTextColumn("MAT_ID", "Material", 140);
            grdLot.AddTextColumn("LOT_QTY", "수량", 80);
            grdLot.AddTextColumn("LOT_STATUS", "상태", 90);
        }

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            if (_isFirstLoaded) return;

            this._lineId = UserInfo.LineId;
            this._operId = UserInfo.OperId;
            _isFirstLoaded = true;
        }

        private void btnSearch_Click(object sender, RoutedEventArgs e)
        {
            SearchLot();
        }

        private void btnConfirm_Click(object sender, RoutedEventArgs e)
        {
            Confirm();
        }

        private void SearchLot()
        {
            ShowLoading(true);

            _sqlManager.Init();
            _sqlManager.AddParam("lotId", txtLotId.Text.Trim());
            _sqlManager.AddParam("appName", _appName);

            DataTable dt = _sqlManager.DPICALL("lot.selectMcLot");

            List<string> tmpList = new List<string>();
            foreach (DataRow row in dt.Rows)
            {
                tmpList.Add(row["LOT_ID"].ToString());
            }

            grdLot.ItemsSource = dt.DefaultView;
            StatusMessage = tmpList.Count + "건 조회";

            ShowLoading(false);
        }

        private void SearchLotByLine()
        {
            ShowLoading(true);

            _sqlManager.Init();
            _sqlManager.AddParam("lineId", cboLine.Text.Trim());
            _sqlManager.AddParam("appName", _appName);

            DataTable dt = _sqlManager.DPICALL("lot.selectMcLotWithLine");

            List<string> tmpList = new List<string>();
            foreach (DataRow row in dt.Rows)
            {
                tmpList.Add(row["LOT_ID"].ToString());
            }

            grdLot.ItemsSource = dt.DefaultView;
            StatusMessage = tmpList.Count + "건 조회";

            ShowLoading(false);
        }

        private bool CheckLot(string lotId)
        {
            _sqlManager.Init();
            _sqlManager.AddParam("lotId", lotId);
            DataTable dt = _sqlManager.DPICALL("lot.selectMcLot");

            if (dt.Rows.Count == 0) return true;

            string status = dt.Rows[0]["LOT_STATUS"].ToString();
            return status == "WAIT" || status == "HELD";
        }

        private void Confirm()
        {
            if (grdLot.SelectedItems == null || grdLot.SelectedItems.Count == 0)
            {
                MessageBox.Show("Lot 을 선택하세요.");
                return;
            }

            ShowLoading(true);

            List<string> targetList = new List<string>();
            foreach (DataRowView drv in grdLot.SelectedItems)
            {
                targetList.Add(drv["LOT_ID"].ToString());
            }

            int okCount = 0;
            int ngCount = 0;
            List<string> ngList = new List<string>();

            foreach (string lotId in targetList)
            {
                if (!CheckLot(lotId))
                {
                    ngCount++;
                    ngList.Add(lotId);
                    continue;
                }

                _sqlManager.Init();
                _sqlManager.AddParam("lotId", lotId);
                _sqlManager.AddParam("attr", "MOVED");
                _sqlManager.AddParam("operId", _operId);

                int affected = _sqlManager.DPIEXEC("lot.updateLotAttr");
                if (affected > 0)
                {
                    okCount++;
                }
                else
                {
                    ngCount++;
                    ngList.Add(lotId);
                }

                _ruleManager.Init();
                _ruleManager.AddParam("lotId", lotId);
                _ruleManager.AddParam("lineId", _lineId);
                _ruleManager.Run("EDS_MOVE_OUT");
            }

            string msg = "확정 " + okCount + "건";
            if (ngCount > 0)
            {
                msg = msg + " / 실패 " + ngCount + "건";
                msg = msg + " (" + string.Join(",", ngList.ToArray()) + ")";
            }

            StatusMessage = msg;
            MessageBox.Show(msg);

            SearchLot();
            ShowLoading(false);
        }

        private string FormatLotId(string lotId)
        {
            if (string.IsNullOrEmpty(lotId)) return string.Empty;
            return lotId.Trim().ToUpper().PadLeft(12, '0');
        }

        private void ShowLoading(bool show)
        {
            Mouse.OverrideCursor = show ? Cursors.Wait : null;
        }
    }
}
