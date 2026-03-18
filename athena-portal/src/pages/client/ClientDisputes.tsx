import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Loader2 } from "lucide-react";
import { getDisputeStatusColor } from "@/lib/mock-data-extended";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCustomerDisputes, fileDispute, type DisputeRecord } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

export default function ClientDisputes() {
  const { customerId } = useAuth();
  const cid = customerId ?? 1;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [field, setField] = useState("");
  const [disputeType, setDisputeType] = useState("");
  const [description, setDescription] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["client-disputes", cid],
    queryFn: () => fetchCustomerDisputes(cid),
  });

  const disputes = data?.disputes || [];

  const fileMutation = useMutation({
    mutationFn: (body: { field: string; reason: string; description: string }) => fileDispute(cid, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-disputes", cid] });
      toast({ title: "Dispute filed", description: "Your dispute has been submitted successfully." });
      setField("");
      setDisputeType("");
      setDescription("");
      setDialogOpen(false);
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to file dispute" });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Disputes</h1>
          <p className="text-sm text-muted-foreground">File and track credit report disputes.</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="mr-2 h-4 w-4" /> File Dispute</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>File a New Dispute</DialogTitle></DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Field / Account Reference</Label>
                <Input placeholder="Enter field or account reference" value={field} onChange={(e) => setField(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Dispute Type</Label>
                <Select value={disputeType} onValueChange={setDisputeType}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="incorrect_balance">Incorrect Balance</SelectItem>
                    <SelectItem value="identity_theft">Identity Theft</SelectItem>
                    <SelectItem value="duplicate_entry">Duplicate Entry</SelectItem>
                    <SelectItem value="closed_not_updated">Closed Not Updated</SelectItem>
                    <SelectItem value="wrong_status">Wrong Status</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Describe the issue in detail..." rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
              <Button
                className="w-full"
                disabled={fileMutation.isPending}
                onClick={() => fileMutation.mutate({ field, reason: disputeType, description })}
              >
                {fileMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Submit Dispute
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="border-border/50">
        <CardHeader><CardTitle className="text-base">Dispute History</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Field</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Filed</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : disputes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">No disputes filed yet.</TableCell>
                </TableRow>
              ) : (
                disputes.map((d: DisputeRecord) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-mono text-xs">{d.id}</TableCell>
                    <TableCell className="text-sm">{d.field || d.reason || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getDisputeStatusColor((d.status || "open").toLowerCase() as any)}>
                        {d.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{d.filed || d.created_at || "—"}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{d.desc || d.description || "—"}</TableCell>
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
