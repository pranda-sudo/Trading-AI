#property strict
#property version "3.00"
input int PollSeconds=15;
input int MaxObjectsPerChart=6000;
input int MaxRows=2000;
string Kind(string n){
 StringToUpper(n);
 if(StringFind(n,"NAKED")>=0 && StringFind(n,"POC")>=0)return "NAKED_POC_CANDIDATE";
 if(StringFind(n,"CDPE")==0 && StringFind(n,"POC")>=0)return "CANDLE_POC_CANDIDATE";
 if(StringFind(n,"IMBALANCE")==0)return "IMBALANCE_CANDIDATE";
 if(StringFind(n,"VPLINE_")==0 || StringFind(n,"CDPP")>=0)return "PROFILE_OBJECT";
 return "";
}
string IntProp(long c,string n,ENUM_OBJECT_PROPERTY_INTEGER p,int i=0){
 long v=0;if(!ObjectGetInteger(c,n,p,i,v))return "";return IntegerToString(v);
}
string Price(long c,string n,int i){
 double v=0;if(!ObjectGetDouble(c,n,OBJPROP_PRICE,i,v)||!MathIsValidNumber(v)||v==EMPTY_VALUE)return "";return DoubleToString(v,8);
}
string Clean(string s){StringReplace(s,",",";");StringReplace(s,"\r"," ");StringReplace(s,"\n"," ");StringReplace(s,"\"","'");return s;}
int OnInit(){if(PollSeconds<10||MaxRows<1||MaxObjectsPerChart<1)return INIT_PARAMETERS_INCORRECT;if(!EventSetTimer(PollSeconds))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnDeinit(const int reason){EventKillTimer();}
void OnTick(){}
void OnTimer(){
 string tmp="TradingAI_CD_Objects_V3.tmp",dst="TradingAI_CD_Objects_V3.csv";
 int f=FileOpen(tmp,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("V3 open error ",GetLastError());return;}
 FileWrite(f,"observed_utc_epoch","symbol","timeframe","chart_id","kind","name","window","type","time0_mt5","price0","time1_mt5","price1","color_bgr","style","width","text","status");
 int rows=0;bool partial=false;long c=ChartFirst();
 while(c>=0 && !IsStopped()){
  string sym=ChartSymbol(c),upper=sym;StringToUpper(upper);
  if(StringFind(upper,"XAUUSD")>=0){
   int total=ObjectsTotal(c,-1,-1);
   if(total>MaxObjectsPerChart||total<0)partial=true;
   for(int i=0;i<MathMin(total,MaxObjectsPerChart)&&!IsStopped();i++){
    string n=ObjectName(c,i,-1,-1),k=Kind(n);if(k=="")continue;
    int win=ObjectFind(c,n);if(win<0)continue;
    if(rows>=MaxRows){partial=true;break;}
    FileWrite(f,IntegerToString((long)TimeGMT()),sym,EnumToString(ChartPeriod(c)),IntegerToString(c),k,Clean(n),win,IntProp(c,n,OBJPROP_TYPE),IntProp(c,n,OBJPROP_TIME,0),Price(c,n,0),IntProp(c,n,OBJPROP_TIME,1),Price(c,n,1),IntProp(c,n,OBJPROP_COLOR),IntProp(c,n,OBJPROP_STYLE),IntProp(c,n,OBJPROP_WIDTH),Clean(ObjectGetString(c,n,OBJPROP_TEXT)),"OBSERVED_UNVERIFIED");
    rows++;
   }
  }
  if(rows>=MaxRows)break;
  c=ChartNext(c);
 }
 FileFlush(f);FileClose(f);
 if(IsStopped())return;
 if(!FileMove(tmp,FILE_COMMON,dst,FILE_COMMON|FILE_REWRITE)){Print("V3 move error ",GetLastError());return;}
 Print("V3 objects=",rows," partial=",partial,"; diagnostic only");
}
