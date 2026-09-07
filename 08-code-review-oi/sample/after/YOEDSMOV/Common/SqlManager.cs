using System.Collections.Generic;

namespace YOEDSMOV
{
    public class SqlManager
    {
        private string _appName;
        private readonly string DPICALL = "DPICALL";
        private readonly string SQLEXEC = "SQLEXEC";
        private readonly string RV_COM_PUB_SUBJECT = RvMsg.rv_c1_pub_subject;
        private readonly string RV_DPIMGR_TARGET = RvMsg.rv_c1_dpimgr_target;
        private readonly string RV_DPIMGR_SUBJECT = RvMsg.rv_c1_dpimgr_subject;

        private SqlBuilder _sql = new SqlBuilder()
        {
            param = new Dictionary<string, string>(),
            paramList = new Dictionary<string, string[]>()
        };

        public SqlManager(string appName)
        {
            _appName = appName;
        }

        public RVMessageResult GetMatIdList(GetMatIdListVO vo)
        {
            _sql.Init();
            _sql.param.Add("lotId", vo.lotId);

            _sql.AddSql($@"
                SELECT /*QR220728-023-01*//*OI_YOEDSMOV_2022-7-28_sw1027.chae*/
                       l.lot_id, m.mat_id, l.lot_qty, l.lot_sub_status_seg AS lot_status
                  FROM mc_lot l, mc_mat m
                 WHERE 1=1
                   AND (l.lot_sub_status_seg NOT IN ('WAIT', 'HELD') OR m.mat_sub_status_seg NOT IN ('WAIT', 'HELD'))
                   AND l.object_id = m.lot_object_id
                   AND TRIM(l.lot_id) = {_sql.Bind("lotId")}
                   AND l.line_id = '{vo.lineId}'
            ");

            RVMessageResult rvResult = new TibRVHelper(RV_COM_PUB_SUBJECT).SendMessageWithJSON(SQLEXEC, RV_DPIMGR_TARGET, RV_DPIMGR_SUBJECT, _appName, _sql.GetSql(), 60);

            return rvResult;
        }

        public RVMessageResult GetLotStatus(GetLotStatusVO vo)
        {
            Dictionary<string, string> param = new Dictionary<string, string>
            {
                { "lotId", vo.lotId },
                { "lineId", vo.lineId }
            };

            RVMessageResult rvResult = new TibRVHelper(RV_COM_PUB_SUBJECT).SendMessageWithJSON(DPICALL, RV_DPIMGR_TARGET, RV_DPIMGR_SUBJECT, "lot.selectMcLotWithLine", _appName, param);

            return rvResult;
        }

        public RVMessageResult GetLotInfoList(LotInfoVO vo)
        {
            _sql.param.Add("lotId", vo.lotId);

            _sql.AddSql($@"
                SELECT l.lot_id, l.lot_qty
                  FROM mc_lot l
                 WHERE l.lot_id = '{vo.lotId}'
            ");

            RVMessageResult rvResult = new TibRVHelper(RV_COM_PUB_SUBJECT).SendMessageWithJSON(SQLEXEC, RV_DPIMGR_TARGET, RV_DPIMGR_SUBJECT, _appName, _sql.GetSql(), 60);

            return rvResult;
        }
    }
}
