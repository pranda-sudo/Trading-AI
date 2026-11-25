#property strict
#property version "4.10"
#property description "Read-only unified diagnostic bridge; attach to existing XAUUSD M5 source chart"
input bool ProductionFiles=false;
input bool ReadOtherGoldM1=false;
input bool EnableObjects=false;
input int SlowReadMs=1500;
input int DiscoverySeconds=60;
input int PollSeconds=5;
input int ObjectSeconds=300;
input int MaxScanPerTimer=50;
input int MaxObjectRows=3000;
string live,objects;
ulong lastLive=0,lastObjects=0,scanStarted=0;
int cursor=0,total=0,of=INVALID_HANDLE,objectRows=0;
datetime scanBar=0;
int handles[4];string names[4];
ulong lastDiscovery=0;
bool objectsPaused=false;
int Slot(string k){if(k=="VWAP")return 0;if(k=="VOLUME")return 1;if(k=="DELTA")return 2;if(k=="CUM_DELTA")return 3;return -1;}
void ReleaseHandles(){for(int i=0;i<4;i++){if(handles[i]!=INVALID_HANDLE)IndicatorRelease(handles[i]);handles[i]=INVALID_HANDLE;names[i]="";}}
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
bool Discover(){
 ulong started=GetTickCount64();
 int windows=(int)ChartGetInteger(0,CHART_WINDOWS_TOTAL);
 Print("V4.1 discovery windows=",windows," err=",GetLastError());
 if(windows<=0)return false;
 bool seen[4];ArrayInitialize(seen,false);
 for(int w=0;w<windows&&!IsStopped();w++){
  ResetLastError();int count=ChartIndicatorsTotal(0,w);
  Print("V4.1 window=",w," count=",count," err=",GetLastError());
  for(int i=0;i<count&&!IsStopped();i++){
   string name=ChartIndicatorName(0,w,i),kind=Kind(name);int k=Slot(kind);
   Print("V4.1 indicator=",name," mapped=",kind);
   if(k<0)continue;
   if(seen[k]){Print("V4.1 ambiguous kind=",kind);ReleaseHandles();return false;}
   seen[k]=true;
   if(handles[k]!=INVALID_HANDLE&&names[k]==name)continue;
   if(handles[k]!=INVALID_HANDLE)IndicatorRelease(handles[k]);
   ResetLastError();handles[k]=ChartIndicatorGet(0,w,name);names[k]=name;
   Print("V4.1 handle kind=",kind," handle=",handles[k]," error=",GetLastError());
  }
 }
 for(int k=0;k<4;k++)if(!seen[k]){if(handles[k]!=INVALID_HANDLE)IndicatorRelease(handles[k]);handles[k]=INVALID_HANDLE;names[k]="";}
 Print("V4.1 discovery ms=",GetTickCount64()-started);
 return true;
}
void ReadChart(int f,long c,int &rows,int &good){
 if(c!=ChartID())return;
 string kinds[4]={"VWAP","VOLUME","DELTA","CUM_DELTA"};
 datetime t0=iTime(_Symbol,_Period,0),t1=iTime(_Symbol,_Period,1);
 for(int k=0;k<4&&!IsStopped();k++){
  string kind=kinds[k];int h=handles[k],nb=k==0?7:1;
  ResetLastError();int ready=h==INVALID_HANDLE?-1:BarsCalculated(h);
  for(int b=0;b<nb;b++){
   double v[2];ResetLastError();int got=-1;
   if(ready>=2)got=CopyBuffer(h,b,0,2,v);
   int err=GetLastError();
   for(int sh=0;sh<=1;sh++){
    datetime t=sh==0?t0:t1;
    string status="OBSERVED_UNVERIFIED",val="";
    if(h==INVALID_HANDLE)status="HANDLE_MISSING";
    else if(got!=2||t<=0)status="BUFFER_WAIT";
    else if(!MathIsValidNumber(v[1-sh])||v[1-sh]==EMPTY_VALUE)status="EMPTY";
    else if((k==0||k==1)&&v[1-sh]<=0)status="ZERO_OR_INVALID";
    else if(err!=0)status="BUFFER_ERROR";
    else if(iTime(_Symbol,_Period,0)!=t0)status="BAR_CHANGED";
    else {val=DoubleToString(v[1-sh],8);good++;}
    FileWrite(f,_Symbol,_Symbol,EnumToString(_Period),c,Clean(names[k]),kind,b,sh,(long)t,(long)TimeGMT(),val,status,err);rows++;
    if(status!="OBSERVED_UNVERIFIED")Print("V4.1 rejected ",kind," b=",b," sh=",sh," status=",status," ready=",ready," got=",got," err=",err);
   }
  }
 }
}
void Live(){
 ulong started=GetTickCount64();int f=FileOpen(live+".tmp",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("V4 live open error ",GetLastError());return;}
 FileWrite(f,"symbol","broker_symbol","timeframe","chart_id","indicator","kind","buffer","shift","bar_time_mt5","observed_utc","value","status","error");
 int rows=0,good=0;
 ReadChart(f,ChartID(),rows,good);
 FileFlush(f);FileClose(f);
 if(!IsStopped())ReplaceFile(live);
 ulong elapsed=GetTickCount64()-started;
 Print("V4.1 live rows=",rows," valid=",good," ms=",elapsed);
 if(elapsed>(ulong)SlowReadMs||good<20){objectsPaused=true;if(of!=INVALID_HANDLE)AbortScan("live degraded");}
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
 if(ProductionFiles||ReadOtherGoldM1||DiscoverySeconds<30||SlowReadMs<100)return INIT_PARAMETERS_INCORRECT;
 ArrayInitialize(handles,INVALID_HANDLE);
 live="TradingAI_CD_Live_V41_test.csv";
 objects="TradingAI_CD_Objects_V41_test.csv";
 if(!EventSetTimer(1))return INIT_FAILED;
 Print("V4.1 started; TEST ONLY objects=",EnableObjects);return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();if(of!=INVALID_HANDLE)AbortScan("deinit");ReleaseHandles();}
void OnTick(){}
void OnTimer(){
 ulong now=GetTickCount64();
 if(lastDiscovery==0||now-lastDiscovery>=(ulong)DiscoverySeconds*1000){ulong d=GetTickCount64();bool ok=Discover();lastDiscovery=GetTickCount64();if(!ok){ReleaseHandles();objectsPaused=true;}if(lastDiscovery-d>(ulong)SlowReadMs)objectsPaused=true;}
 if(lastLive==0||now-lastLive>=(ulong)PollSeconds*1000){Live();lastLive=GetTickCount64();}
 if(EnableObjects&&!objectsPaused&&!IsStopped())ScanSlice();
}
