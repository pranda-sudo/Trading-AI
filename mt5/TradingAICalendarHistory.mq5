#property strict
#property script_show_inputs
// Trading AI: one-off historical calendar backfill, separate from live exporter.
// Run once via MT5 Navigator > Scripts. Does not place trades.
input int DaysBehind=1100;
input int ChunkDays=60;
input string CurrencyFilter="USD,EUR";
input string OutputFile="trading_ai_calendar_history.csv";
bool Allowed(string currency){return StringFind(","+CurrencyFilter+",",","+currency+",")>=0;}
string NumberValue(long value){if(value==LONG_MIN)return "";return DoubleToString((double)value/1000000.0,6);}
string ISO(datetime t){string s=TimeToString(t,TIME_DATE|TIME_SECONDS);StringReplace(s,".","-");StringReplace(s," ","T");return s+"Z";}
void OnStart(){
 if(DaysBehind<1||DaysBehind>3650||ChunkDays<1||ChunkDays>365){Print("Invalid days parameters");return;}
 datetime now=TimeTradeServer();
 if(now<=0){Print("TimeTradeServer unavailable");return;}
 int handle=FileOpen(OutputFile,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
 if(handle==INVALID_HANDLE){Print("Unable to create history CSV: ",GetLastError());return;}
 FileWrite(handle,"event_key","event_id","value_id","event_time","currency","country","title","importance","previous_value","forecast_value","actual_value","unit");
 // MT5 calendar times are in trade-server time. Current offset is an approximation
 // for historical dates if broker server changes DST. Validate before backtesting.
 int offset=(int)(TimeTradeServer()-TimeGMT());
 datetime start=now-(datetime)((long)DaysBehind*86400);
 int total=0,failed=0,windows=0;
 for(datetime from=start;from<now;from+=(datetime)(ChunkDays*86400)){
  datetime until=from+(datetime)(ChunkDays*86400);
  if(until>now)until=now;
  MqlCalendarValue values[];
  ResetLastError();
  int count=CalendarValueHistory(values,from,until);
  windows++;
  if(count<0){failed++;Print("Calendar chunk failed ",TimeToString(from,TIME_DATE)," code ",GetLastError());continue;}
  for(int i=0;i<count;i++){
   MqlCalendarEvent ev;
   if(!CalendarEventById(values[i].event_id,ev))continue;
   MqlCalendarCountry country;
   if(!CalendarCountryById(ev.country_id,country))continue;
   if(!Allowed(country.currency)||ev.importance<1)continue;
   string key=StringFormat("%I64d",values[i].id);
   FileWrite(handle,key,StringFormat("%I64d",ev.id),key,ISO(values[i].time-offset),
      country.currency,country.code,ev.name,IntegerToString((int)ev.importance),
      NumberValue(values[i].prev_value),NumberValue(values[i].forecast_value),
      NumberValue(values[i].actual_value),EnumToString(ev.unit));
   total++;
  }
  Print("Calendar history chunk ",windows,": ",TimeToString(from,TIME_DATE)," events ",count);
 }
 FileClose(handle);
 Print("Trading AI historical export completed: ",total," rows; failed chunks ",failed,
       "; file Common\\Files\\",OutputFile,
       ". WARNING historical DST offset needs verification.");
}
