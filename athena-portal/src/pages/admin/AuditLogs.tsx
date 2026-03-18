import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { mockAuditLogs } from "@/lib/mock-data-extended";
import { useQuery } from "@tanstack/react-query";
import { fetchAuditLogs, type AuditEntry } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

function getActionColor(action: string) {
  if (action.includes("VIEW") || action.includes("DOWNLOAD") || action.includes("GET")) return "bg-blue-500/10 text-blue-600 border-blue-500/20";
  if (action.includes("RESOLVE") || action.includes("UPDATE") || action.includes("PUT")) return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
  if (action.includes("FREEZE") || action.includes("DELETE")) return "bg-red-500/10 text-red-600 border-red-500/20";
  return "bg-muted text-muted-foreground border-border";
}

export default function AuditLogs() {
  const { data: apiLogs, isLoading, isError } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => fetchAuditLogs(0, 50),
  });

  const logs = isError || !apiLogs || apiLogs.length === 0 ? mockAuditLogs : apiLogs;
  const useMock = isError || !apiLogs || apiLogs.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Audit Logs</h1>
        <p className="text-sm text-muted-foreground">System activity log for compliance and security monitoring.</p>
      </div>

      <Card className="border-border/50">
        <CardHeader><CardTitle className="text-base">Recent Activity</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>IP Address</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                logs.map((log: any) => {
                  const timestamp = useMock ? log.timestamp : (log.ts || log.timestamp || "");
                  const userName = useMock ? log.userName : (log.partner || log.userName || "—");
                  const action = useMock ? log.action : (log.action || "—");
                  const resource = useMock ? log.resource : (log.customer || log.resource || "—");
                  const details = useMock ? log.details : (log.outcome || log.details || "—");
                  const ip = useMock ? log.ipAddress : (log.ip || log.ipAddress || "—");

                  return (
                    <TableRow key={log.id}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {timestamp ? new Date(timestamp).toLocaleString() : "—"}
                      </TableCell>
                      <TableCell className="text-sm font-medium">{userName}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`text-xs ${getActionColor(action)}`}>
                          {action}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{resource}</TableCell>
                      <TableCell className="text-sm max-w-xs truncate">{details}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{ip}</TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
