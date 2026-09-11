using System;
using System.Globalization;
using System.Windows.Data;

namespace YOEDSMOV.Common
{
    /// <summary>
    /// Lot 상태 코드를 화면에 보여줄 말로 바꿉니다.
    /// C# 어디에서도 호출하지 않습니다 — XAML 의 {StaticResource} 로만 쓰입니다.
    /// </summary>
    public class LotStatusConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            string code = value as string;
            if (string.IsNullOrEmpty(code)) return string.Empty;

            switch (code)
            {
                case "WAIT": return "대기";
                case "HELD": return "보류";
                case "MOVED": return "반출완료";
                default: return code;
            }
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }
}
