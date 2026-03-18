import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, CheckCircle, XCircle } from "lucide-react";
import { mockDisputes, getDisputeTypeLabel, getDisputeStatusColor } from "@/lib/mock-data-extended";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAllDisputes, updateDisputeStatus, type DisputeRecord } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

function disputeId(d: DisputeRecord): string {
  return String(d.id);
}

function disputeCustomer(d: DisputeRecord): string {
  return d.customer || `Customer ${d.customerId || d.customer_id || "—"}`;
}

function disputeField(d: DisputeRecord): string {
  return d.field || d.reason || "—";
}

function disputeDesc(d: DisputeRecord): string {
  return d.desc || d.description || "—";
}

function disputeStatus(d: DisputeRecord): string {
  return (d.status || "open").toLowerCase();
}

function disputeFiled(d: DisputeRecord): string {
  return d.filed || d.created_at || "—";
}

export default function AdminDisputes() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: apiDisputes, isLoading, isError } = useQuery({
    queryKey: ["admin-disputes"],
    queryFn: () => fetchAllDisputes(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number | string; status: string }) => updateDisputeStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-disputes"] });
      toast({ title: "Dispute updated" });
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to update dispute" });
    },
  });

  // Fall back to mock data if API fails
  const disputes = isError ? mockDisputes : (apiDisputes || []);
  const useMock = isError || !apiDisputes;

  const statusCounts = {
    open: disputes.filter((d: any) => disputeStatus(d) === "open").length,
    investigating: disputes.filter((d: any) => disputeStatus(d) === "investigating").length,
    resolved: disputes.filter((d: any) => disputeStatus(d) === "resolved").length,
    rejected: disputes.filter((d: any) => disputeStatus(d) === "rejected").length,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dispute Management</h1>
        <p className="text-sm text-muted-foreground">Review and resolve credit report disputes.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Open", count: statusCounts.open, color: "text-blue-600" },
          { label: "Investigating", count: statusCounts.investigating, color: "text-amber-600" },
          { label: "Resolved", count: statusCounts.resolved, color: "text-emerald-600" },
          { label: "Rejected", count: statusCounts.rejected, color: "text-red-500" },
        ].map((s) => (
          <Card key={s.label} className="border-border/50">
            <CardContent className="p-4 text-center">
              <div className={`text-3xl font-bold ${s.color}`}>{isLoading ? "—" : s.count}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border/50">
        <CardHeader><CardTitle className="text-base">All Disputes</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Field</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Filed</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : disputes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">No disputes found.</TableCell>
                </TableRow>
              ) : (
                disputes.map((d: any) => (
                  <TableRow key={disputeId(d)}>
                    <TableCell className="font-mono text-xs">{disputeId(d)}</TableCell>
                    <TableCell className="text-sm font-medium">{useMock ? d.clientName : disputeCustomer(d)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {useMock ? getDisputeTypeLabel(d.type) : disputeField(d)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getDisputeStatusColor(disputeStatus(d) as any)}>
                        {disputeStatus(d)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{useMock ? d.filedDate : disputeFiled(d)}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{useMock ? d.description : disputeDesc(d)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-1 justify-end">
                        <Button variant="ghost" size="icon" className="h-8 w-8"><Eye className="h-3.5 w-3.5" /></Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-emerald-600"
                          disabled={useMock || updateMutation.isPending}
                          onClick={() => updateMutation.mutate({ id: d.id, status: "RESOLVED" })}
                        >
                          <CheckCircle className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500"
                          disabled={useMock || updateMutation.isPending}
                          onClick={() => updateMutation.mutate({ id: d.id, status: "REJECTED" })}
                        >
                          <XCircle className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
