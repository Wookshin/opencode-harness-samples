using System;
using System.Data;
using System.Text;

namespace YOEDSMOV.Common
{
    /// <summary>
    /// DPI 표준 SQL 호출기. mapper 에 등록된 SQL 을 ID 로 부르거나,
    /// 화면에서 조립한 인라인 SQL 을 직접 실행합니다.
    /// </summary>
    public class SqlManager
    {
        private readonly string _appName;
        private DataTable _param;
        private StringBuilder _sql;

        public SqlManager(string appName)
        {
            _appName = appName;
            _param = new DataTable();
            _sql = new StringBuilder();
        }

        public void Init()
        {
            _param = new DataTable();
            _sql = new StringBuilder();
        }

        public void AddParam(string key, object value)
        {
            _param.Columns.Add(key);
            _param.Rows.Add(value);
        }

        public string Bind(string key)
        {
            return "#{" + key + "}";
        }

        public void AddSql(string sql)
        {
            _sql.Append(sql);
        }

        public DataTable DPICALL(string sqlId)
        {
            return DpiGateway.Select(_appName, sqlId, _param);
        }

        public int DPIEXEC(string sqlId)
        {
            return DpiGateway.Execute(_appName, sqlId, _param);
        }

        public DataTable SQLEXEC()
        {
            return DpiGateway.SelectRaw(_appName, _sql.ToString(), _param);
        }

        /// <summary>
        /// 라인별 Lot 현황. mapper 에 올리지 않고 화면에서 조립합니다.
        /// </summary>
        public DataTable SelectLotSummary(string lineId, string fromDate)
        {
            Init();

            AddSql("SELECT /*QR220728-023-01*/ ");
            AddSql("       l.lot_id, l.lot_qty, m.mat_id ");
            AddSql("  FROM mc_lot l, mc_mat m ");
            AddSql(" WHERE l.mat_key = m.mat_key ");
            AddSql("   AND TRIM(l.line_id) = '" + lineId + "' ");
            AddSql("   AND l.crt_tmstp >= '" + fromDate + "' ");

            return SQLEXEC();
        }

        public string BuildWhere(string lotId)
        {
            string where = " WHERE 1=1 ";
            if (!string.IsNullOrEmpty(lotId))
            {
                where = where + " AND lot_id = '" + lotId + "' ";
            }
            return where;
        }
    }
}
