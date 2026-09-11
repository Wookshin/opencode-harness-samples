using System.Data;

namespace YOEDSMOV.Common
{
    /// <summary>표준 룰 엔진 호출기.</summary>
    public class RuleManager
    {
        private readonly string _appName;
        private DataTable _param;

        public RuleManager(string appName)
        {
            _appName = appName;
            _param = new DataTable();
        }

        public void Init()
        {
            _param = new DataTable();
        }

        public void AddParam(string key, object value)
        {
            _param.Columns.Add(key);
            _param.Rows.Add(value);
        }

        public void Run(string ruleId)
        {
            DpiGateway.RunRule(_appName, ruleId, _param);
        }
    }
}
