using System;
using System.Collections.Generic;
using System.Data;
using System.Windows;
using System.Windows.Controls;

namespace YOEDSMOV
{
    /// <summary>
    /// EDS 반출 화면. Lot 을 선택해 반출 확정을 겁니다.
    /// </summary>
    public partial class YOEDSMOV : UserControl
    {
        private readonly SqlManager _sqlManager = new SqlManager("YOEDSMOV");
        private readonly RuleManager _ruleManager = new RuleManager("YOEDSMOV");

        private string _appName = "YOEDSMOV";
        private string _lineId = string.Empty;
        private string _operId = string.Empty;
        private bool _isFirstLoaded = false;

        private RVMessageResult _rvResult = null;

        public YOEDSMOV()
        {
            InitializeComponent();
            InitGridColumns();
        }

        private void InitGridColumns()
        {
            grdLot.Columns.Clear();
            grdLot.AddTextColumn("LOT_ID", "Lot ID", 140);
            grdLot.AddTextColumn("MAT_ID", "Material", 140);
            grdLot.AddTextColumn("LOT_QTY", "수량", 80);
        }

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            if (_isFirstLoaded) return;

            _lineId = UserInfo.LineId;
            _operId = UserInfo.OperId;
            _isFirstLoaded = true;
        }

        private void btnSearch_Click(object sender, RoutedEventArgs e)
        {
            Search();
        }

        private void Search()
        {
            ShowLoading(true);

            GetMatIdListVO vo = new GetMatIdListVO
            {
                lotId = txtLotId.Text.Trim()
            };

            _rvResult = _sqlManager.GetMatIdList(vo);

            if (!_rvResult.IsSuccess)
            {
                ShowLoading(false);
                MessageBox.Show(_rvResult.Message);
                return;
            }

            grdLot.ItemsSource = _rvResult.DataTable.DefaultView;
            ShowLoading(false);
        }

        private void btnConfirm_Click(object sender, RoutedEventArgs e)
        {
            Confirm();
        }

        private void Confirm()
        {
            DataRowView drv = grdLot.SelectedItem as DataRowView;
            if (drv == null)
            {
                MessageBox.Show("Lot 을 선택하세요.");
                return;
            }

            string lotId = drv["LOT_ID"].ToString();
            string sLotQty = drv["LOT_QTY"].ToString();

            ModAttrVO vo = new ModAttrVO
            {
                lotId = lotId,
                operId = _operId,
                attr = string.Format("(EDS_MOV_QTY={0})", sLotQty)
            };

            _rvResult = _ruleManager.SendModAttr(vo);

            if (!_rvResult.IsSuccess)
            {
                MessageBox.Show(_rvResult.Message);
                return;
            }

            MessageBox.Show("반출 확정되었습니다.");
            Search();
        }

        private void ShowLoading(bool isVisible)
        {
            loading.Visibility = isVisible ? Visibility.Visible : Visibility.Collapsed;
            btnSearch.IsEnabled = !isVisible;
            btnConfirm.IsEnabled = !isVisible;
        }
    }
}
