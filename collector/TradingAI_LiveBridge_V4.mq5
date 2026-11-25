#property strict
#property version "4.00"
#property description "Read-only unified diagnostic bridge; attach to existing XAUUSD M5 source chart"
input bool ProductionFiles=false;
input bool ReadOtherGoldM1=false;
input int PollSeconds=5;
input int ObjectSeconds=15;
input int MaxScanPerTimer=250;
input int MaxObjectRows=3000;
string live,objects;
ulong lastLive=0,lastObjects=0,scanStarted=0;
int cursor=0,total=0,of=INVALID_HANDLE,objectRows=0;
datetime scanBar=0;
string Kind(string n){
 StringToLower(n);
 if(StringFind(n,"vwap")>=0)return "VWAP";
 if(StringFind(n,"cum")>=0 && StringFind(n,"delta")>=0)return "CUM_DELTA";
 if(StringFind(n,"#delta")>=0 || StringFind(n,"clusterdelta delta")>=0)return "DELTA";
 if(StringFind(n,"#volumes")>=0 || StringFind(n,"clusterdelta volume")>=0)return "VOLUME";
 return "";
}
string ObjKind(string n){
 StringToUpper(n);
 if(StringFind(n,"CDPE")==0 && StringFind(n,"POC")>=0)return "CANDLE_POC_CANDIDATE";
 if(StringFind(n,"IMBALANCE")==0)return "IMBALANCE_CANDIDATE";
 if(StringFind(n,"VPLINE_")==0 || StringFind(n,"CDPP")>=0)return "PROFILE_OBJECT";
 return "";
}
string IP(string n,ENUM_OBJECT_PROPERTY_INTEGER p,int i=0){
 long v=0;if(!ObjectGetInteger(0,n,p,i,v))return "";return IntegerToString(v);
}
string Price(string n,int i){
 double v=0;if(!ObjectGetDouble(0,n,OBJPROP_PRICE,i,v)||!MathIsValidNumber(v)||v==EMPTY_VALUE)return "";return DoubleToString(v,8);
}
string Clean(string s){StringReplace(s,",",";");StringReplace(s,"\r"," ");StringReplace(s,"\n"," ");StringReplace(s,"\"","'");return s;}
bool ReplaceFile(string dest){
 ResetLastError();
 if(FileMove(dest+".tmp",FILE_COMMON,dest,FILE_COMMON|FILE_REWRITE))return true;
 Print("V4 replace failed ",dest," error=",GetLastError());return false;
}
void ReadChart(int f,long c,int &rows,int &good){
 string sym=ChartSymbol(c);ENUM_TIMEFRAMES tf=ChartPeriod(c);
 if(sym!="XAUUSD" || (tf!=PERIOD_M5 && tf!=PERIOD_M1))return;
 int windows=(int)ChartGetInteger(c,CHART_WINDOWS_TOTAL);
 for(int w=0;w<windows&&!IsStopped();w++){
  int count=ChartIndicatorsTotal(c,w);
  for(int i=0;i<count&&!IsStopped();i++){
   string name=ChartIndicatorName(c,w,i),kind=Kind(name);if(kind=="")continue;
   ResetLastError();int h=ChartIndicatorGet(c,w,name);int err=GetLastError();
   if(h==INVALID_HANDLE){FileWrite(f,sym,sym,EnumToString(tf),c,Clean(name),kind,0,-1,0,(long)TimeGMT(),"","HANDLE_ERROR",err);rows++;continue;}
   int ready=BarsCalculated(h),nb=kind=="VWAP"?7:1;
   for(int b=0;b<nb;b++)for(int sh=0;sh<=1;sh++){
    datetime t=iTime(sym,tf,sh);double v[1];ResetLastError();
    int got=-1;if(ready>sh)got=CopyBuffer(h,b,sh,1,v);
    err=GetLastError();datetime after=iTime(sym,tf,sh);
    string status="OBSERVED_UNVERIFIED",val="";
    if(got!=1 || t<=0 || t!=after)status="BUFFER_WAIT";
    else if(!MathIsValidNumber(v[0])||v[0]==EMPTY_VALUE)status="EMPTY";
    else if((kind=="VWAP"||kind=="VOLUME")&&v[0]<=0)status="ZERO_OR_INVALID";
    else if(err!=0)status="BUFFER_ERROR";
    else {val=DoubleToString(v[0],8);good++;}
    FileWrite(f,sym,sym,EnumToString(tf),c,Clean(name),kind,b,sh,(long)t,(long)TimeGMT(),val,status,err);rows++;
   }
   IndicatorRelease(h);
  }
 }
}
void Live(){
 ulong started=GetTickCount64();int f=FileOpen(live+".tmp",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("V4 live open error ",GetLastError());return;}
 FileWrite(f,"symbol","broker_symbol","timeframe","chart_id","indicator","kind","buffer","shift","bar_time_mt5","observed_utc","value","status","error");
 int rows=0,good=0;
 ReadChart(f,ChartID(),rows,good);
 if(ReadOtherGoldM1 && !IsStopped()){
  for(long c=ChartFirst();c>=0&&!IsStopped();c=ChartNext(c)){
   if(c!=ChartID()&&ChartSymbol(c)=="XAUUSD"&&ChartPeriod(c)==PERIOD_M1){ReadChart(f,c,rows,good);break;}
  }
 }
 FileFlush(f);FileClose(f);
 if(!IsStopped())ReplaceFile(live);
 Print("V4 live rows=",rows," valid=",good," ms=",GetTickCount64()-started);
}
void AbortScan(string why){
 if(of!=INVALID_HANDLE){FileClose(of);of=INVALID_HANDLE;}
 FileDelete(objects+".tmp",FILE_COMMON);
 Print("V4 objects aborted: ",why);
 lastObjects=GetTickCount64();
}
void ScanSlice(){
 ulong now=GetTickCount64();
 if(of==INVALID_HANDLE){
  if(lastObjects!=0 && now-lastObjects<(ulong)ObjectSeconds*1000)return;
  total=ObjectsTotal(0,-1,-1);cursor=0;objectRows=0;scanStarted=now;scanBar=iTime(_Symbol,PERIOD_M5,0);
  if(total<0||scanBar<=0){lastObjects=now;return;}
  of=FileOpen(objects+".tmp",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
  if(of==INVALID_HANDLE){Print("V4 objects open error ",GetLastError());lastObjects=now;return;}
  FileWrite(of,"observed_utc_epoch","symbol","timeframe","chart_id","kind","name","window","type","time0_mt5","price0","time1_mt5","price1","color_bgr","style","width","text","status");
 }
 if(now-scanStarted>90000 || iTime(_Symbol,PERIOD_M5,0)!=scanBar){AbortScan("timeout or new bar");return;}
 int end=(int)MathMin(total,cursor+MaxScanPerTimer);
 for(;cursor<end&&!IsStopped();cursor++){
  if(GetTickCount64()-now>200)break;
  string n=ObjectName(0,cursor,-1,-1),k=ObjKind(n);if(k=="")continue;
  if(k=="CANDLE_POC_CANDIDATE"){
   // Reject old objects using the known CDPE name format before property reads.
   int pos=StringFind(n,"_");
   if(pos<0)continue;
   datetime named=StringToTime(StringSubstr(n,pos+1,16));
   if(named<scanBar-900||named>scanBar)continue;
  }
  long t=0;if(!ObjectGetInteger(0,n,OBJPROP_TIME,0,t)||t<=0)continue;
  if(k=="CANDLE_POC_CANDIDATE" && (t<scanBar-900||t>=scanBar))continue;
  if(k=="IMBALANCE_CANDIDATE" && (t<scanBar-3600||t>scanBar))continue;
  if(k=="PROFILE_OBJECT" && (t<scanBar-86400||t>scanBar))continue;
  string p=Price(n,0);if(p==""||StringToDouble(p)<=0)continue;
  int win=ObjectFind(0,n);if(win!=0)continue;
  if(objectRows>=MaxObjectRows){AbortScan("row limit");return;}
  FileWrite(of,(long)TimeGMT(),_Symbol,EnumToString(_Period),ChartID(),k,Clean(n),win,IP(n,OBJPROP_TYPE),t,p,IP(n,OBJPROP_TIME,1),Price(n,1),IP(n,OBJPROP_COLOR),IP(n,OBJPROP_STYLE),IP(n,OBJPROP_WIDTH),Clean(ObjectGetString(0,n,OBJPROP_TEXT)),"OBSERVED_UNVERIFIED");
  objectRows++;
 }
 if(IsStopped()){AbortScan("stopping");return;}
 if(cursor>=total){
  if(ObjectsTotal(0,-1,-1)!=total){AbortScan("object count changed");return;}
  FileFlush(of);FileClose(of);of=INVALID_HANDLE;
  ReplaceFile(objects);
  Print("V4 objects rows=",objectRows," scanned=",total," ms=",GetTickCount64()-scanStarted);
  lastObjects=GetTickCount64();
 }
}
int OnInit(){
 if(_Symbol!="XAUUSD"||_Period!=PERIOD_M5||PollSeconds<5||ObjectSeconds<15||MaxScanPerTimer<1||MaxObjectRows<1)return INIT_PARAMETERS_INCORRECT;
 live=ProductionFiles?"TradingAI_CD_Live_V2.csv":"TradingAI_CD_Live_V4_test.csv";
 objects=ProductionFiles?"TradingAI_CD_Objects_V3.csv":"TradingAI_CD_Objects_V4_test.csv";
 if(!EventSetTimer(1))return INIT_FAILED;
 Print("V4 started; production=",ProductionFiles," other M1=",ReadOtherGoldM1);return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();if(of!=INVALID_HANDLE)AbortScan("deinit");}
void OnTick(){}
void OnTimer(){
 ulong now=GetTickCount64();
 if(lastLive==0||now-lastLive>=(ulong)PollSeconds*1000){Live();lastLive=GetTickCount64();}
 if(!IsStopped())ScanSlice();
}
