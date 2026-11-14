import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { RadLabRecord } from "../services/dataService";

const tooltipStyle = { background: "#161819", border: "1px solid #303536", borderRadius: 10, color: "#e9eded", fontSize: 11 };
const axisProps = { tick: { fill: "#687170", fontSize: 10 }, axisLine: { stroke: "#292e2f" }, tickLine: false as const };
export function MissionTrendChart({ data }: { data: Array<Record<string, string | number | null>> }) {
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 6, right: 7, left: -17, bottom: 0 }}>
    <defs><linearGradient id="hrFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#198D6D" stopOpacity={0.28} /><stop offset="92%" stopColor="#198D6D" stopOpacity={0.015} /></linearGradient></defs>
    <CartesianGrid stroke="#242829" strokeDasharray="3 5" vertical={false} />
    <XAxis dataKey="day" {...axisProps} />
    <YAxis yAxisId="hr" {...axisProps} domain={["dataMin - 8", "dataMax + 8"]} />
    <YAxis yAxisId="spo2" orientation="right" hide domain={["dataMin - 2", "dataMax + 2"]} />
    <YAxis yAxisId="temperature" orientation="right" hide domain={["dataMin - 0.5", "dataMax + 0.5"]} />
    <Tooltip contentStyle={tooltipStyle} />
    <Area yAxisId="hr" type="monotone" dataKey="heart_rate" name="Heart rate · bpm" stroke="#42c59b" strokeWidth={2} fill="url(#hrFill)" />
    <Line yAxisId="spo2" type="monotone" dataKey="spo2" name="O₂ saturation · %" stroke="#b99af7" strokeWidth={1.7} dot={false} />
    <Line yAxisId="temperature" type="monotone" dataKey="temperature" name="Body temperature · °C" stroke="#e78262" strokeWidth={1.4} dot={false} />
  </AreaChart></ResponsiveContainer>;
}
export function AdmissionsChart({ data }: { data: Array<{ day: string; checkins: number }> }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 5, right: 5, left: -18, bottom: 0 }}>
    <CartesianGrid stroke="#242829" strokeDasharray="3 5" vertical={false} />
    <XAxis dataKey="day" {...axisProps} /><YAxis {...axisProps} />
    <Tooltip contentStyle={tooltipStyle} />
    <Bar dataKey="checkins" name="Recorded readings" fill="#538bce" radius={[4, 4, 0, 0]} barSize={15} />
  </BarChart></ResponsiveContainer>;
}
export function StatusDonut({ data }: { data: Array<{ name: string; value: number; color: string }> }) {
  return <ResponsiveContainer width="100%" height="100%"><PieChart>
    <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="62%" outerRadius="82%" paddingAngle={3} stroke="none">
      {data.map((item) => <Cell key={item.name} fill={item.color} />)}
    </Pie><Tooltip contentStyle={tooltipStyle} />
  </PieChart></ResponsiveContainer>;
}
export function MetricHistoryChart({ data, unit, bounds }: { data: Array<{ date: string; value: number }>; unit: string; bounds?: { low: number; high: number; median: number } }) {
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 12, right: 12, left: -12, bottom: 0 }}>
    <CartesianGrid stroke="#242829" strokeDasharray="3 5" vertical={false} />
    <XAxis dataKey="date" {...axisProps} /><YAxis {...axisProps} domain={["auto", "auto"]} unit={" " + unit} />
    {bounds && <ReferenceArea y1={bounds.low} y2={bounds.high} fill="#198D6D" fillOpacity={0.1} />}
    {bounds && <ReferenceLine y={bounds.median} stroke="#198D6D" strokeDasharray="4 4" />}
    <Tooltip contentStyle={tooltipStyle} />
    <Line type="monotone" dataKey="value" name={unit} stroke="#61caa5" strokeWidth={2} dot={{ r: 2, fill: "#61caa5" }} activeDot={{ r: 4 }} />
  </LineChart></ResponsiveContainer>;
}

export function RadLabRateChart({ data }: { data: RadLabRecord[] }) {
  const rows = data.filter((item) => item.absorbed_dose_rate !== null).map((item) => ({
    ...item,
    clock: item.timestamp.slice(11, 16),
  }));
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{ top: 12, right: 12, left: -6, bottom: 0 }}>
    <CartesianGrid stroke="#242829" strokeDasharray="3 5" vertical={false} />
    <XAxis dataKey="clock" {...axisProps} minTickGap={24} />
    <YAxis {...axisProps} domain={["auto", "auto"]} unit=" µGy/h" />
    <Tooltip contentStyle={tooltipStyle} labelFormatter={(_, values) => values?.[0]?.payload?.timestamp || ""} formatter={(value: number) => [`${value.toFixed(3)} µGy/hour`, "Absorbed dose rate"]} />
    <Line type="monotone" dataKey="absorbed_dose_rate" name="Absorbed dose rate" stroke="#e9ad61" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
  </LineChart></ResponsiveContainer>;
}
