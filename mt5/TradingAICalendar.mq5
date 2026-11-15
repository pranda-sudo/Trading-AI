#property strict
// Trading AI calendar exporter: attach as Expert Advisor to ONE MT5 chart.
// Exports a rolling 35-day calendar to the terminal's COMMON Files folder.
input int RefreshSeconds=3600;
input int DaysAhead=35;
input int DaysBehind=7;
input string CurrencyFilter="USD,EUR";
string output="trading_ai_calendar.csv";
bool allowed(string currency){return StringFind(","+CurrencyFilter+",",","+currency+",")>=0;}
string number(long value){if(value==LONG_MIN)return "";return DoubleToString((double)value/1000000.0,6);}
string iso(datetime t){string s=TimeToString(t,TIME_DATE|TIME_SECONDS);StringReplace(s,".","-");StringReplace(s," ","T");return s+"Z";}
void ExportCalendar(){
 datetime now=TimeTradeServer();
 datetime from=now-(datetime)(DaysBehind*86400);
 datetime until=now+(datetime)(DaysAhead*86400);
 MqlCalendarValue values[];
 ResetLastError();
 int count=CalendarValueHistory(values,from,until);
 if(count<0){Print("Trading AI calendar error: ",GetLastError());return;}
 int handle=FileOpen(output,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
 if(handle==INVALID_HANDLE){Print("Trading AI calendar file error ",GetLastError());return;}
 FileWrite(handle,"event_key","event_id","value_id","event_time","currency","country","title","importance","previous_value","forecast_value","actual_value","unit");
 int offset=(int)(TimeTradeServer()-TimeGMT());
 int exported=0;
 for(int i=0;i<count;i++){
  MqlCalendarEvent ev;
  if(!CalendarEventById(values[i].event_id,ev))continue;
  MqlCalendarCountry country;
  if(!CalendarCountryById(ev.country_id,country))continue;
  if(!allowed(country.currency))continue;
  if(ev.importance<1)continue;
  string key=StringFormat("%I64d",values[i].id);
  datetime utc=values[i].time-offset;
  FileWrite(handle,key,StringFormat("%I64d",ev.id),key,iso(utc),country.currency,country.code,ev.name,
   IntegerToString((int)ev.importance),number(values[i].prev_value),number(values[i].forecast_value),
   number(values[i].actual_value),EnumToString(ev.unit));
  exported++;
 }
 FileClose(handle);
 Print("Trading AI calendar exported ",exported," events, broker offset seconds ",offset);
}
int OnInit(){EventSetTimer(MathMax(60,RefreshSeconds));ExportCalendar();return INIT_SUCCEEDED;}
void OnTimer(){ExportCalendar();}
void OnDeinit(const int reason){EventKillTimer();}
void OnTick(){}
