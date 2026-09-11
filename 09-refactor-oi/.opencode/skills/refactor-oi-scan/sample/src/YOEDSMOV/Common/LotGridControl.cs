using System.Windows;
using System.Windows.Controls;

namespace YOEDSMOV.Common
{
    /// <summary>
    /// 그리드 한 줄 높이를 XAML 에서 지정할 수 있게 한 컨트롤입니다.
    /// RowHeightProperty 는 C# 에서 직접 부르는 곳이 없습니다 — XAML 속성으로만 쓰입니다.
    /// </summary>
    public class LotGridControl : DataGrid
    {
        public static readonly DependencyProperty RowHeightProperty =
            DependencyProperty.Register("RowHeight", typeof(double), typeof(LotGridControl),
                new PropertyMetadata(24.0));

        public double RowHeight
        {
            get { return (double)GetValue(RowHeightProperty); }
            set { SetValue(RowHeightProperty, value); }
        }
    }
}
