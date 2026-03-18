import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Download, FileText, Eye } from "lucide-react";
import { mockClients, formatCurrency, getScoreColor } from "@/lib/mock-data";

const recentReports = mockClients.map((c) => ({
  id: `RPT-${c.id.split("-")[1]}`,
  clientName: c.name,
  nationalId: c.nationalId,
  date: c.lastReportDate,
  score: c.creditScore,
  source: ["TransUnion", "Metropol", "Athena"][Math.floor(Math.random() * 3)],
  type: ["Full Report", "Summary", "Monitoring"][Math.floor(Math.random() * 3)],
}));

export default function AdminReports() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Credit Reports</h1>
          <p className="text-sm text-muted-foreground">Generated credit reports and history.</p>
        </div>
        <Button><FileText className="mr-2 h-4 w-4" /> Generate Report</Button>
      </div>

      <Card className="border-border/50">
        <CardHeader><CardTitle className="text-base">Recent Reports</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Report ID</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>National ID</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentReports.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">{r.id}</TableCell>
                  <TableCell className="text-sm font-medium">{r.clientName}</TableCell>
                  <TableCell className="font-mono text-sm">{r.nationalId}</TableCell>
                  <TableCell className="text-sm">{r.date}</TableCell>
                  <TableCell className={`font-bold font-mono ${getScoreColor(r.score)}`}>{r.score}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs">{r.source}</Badge></TableCell>
                  <TableCell className="text-sm">{r.type}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-1 justify-end">
                      <Button variant="ghost" size="icon" className="h-8 w-8"><Eye className="h-3.5 w-3.5" /></Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8"><Download className="h-3.5 w-3.5" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
