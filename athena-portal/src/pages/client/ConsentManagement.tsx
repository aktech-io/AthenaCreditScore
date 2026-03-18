import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { mockConsents } from "@/lib/mock-data-extended";
import { ShieldCheck, XCircle, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchConsents, revokeConsent, type ConsentRecord } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

function getConsentStatusColor(status: string) {
  switch (status?.toLowerCase()) {
    case "active": return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
    case "expired": return "bg-muted text-muted-foreground border-border";
    case "revoked": return "bg-red-500/10 text-red-500 border-red-500/20";
    default: return "";
  }
}

export default function ConsentManagement() {
  const { customerId } = useAuth();
  const cid = customerId ?? 1;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: apiConsents, isLoading, isError } = useQuery({
    queryKey: ["client-consents", cid],
    queryFn: () => fetchConsents(cid),
  });

  const revokeMutation = useMutation({
    mutationFn: (consentId: number | string) => revokeConsent(cid, consentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-consents", cid] });
      toast({ title: "Consent revoked" });
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to revoke consent" });
    },
  });

  const useMock = isError || !apiConsents;
  const consents = useMock ? mockConsents : apiConsents;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Consent Management</h1>
        <p className="text-sm text-muted-foreground">Control who can access your credit information.</p>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Active Consents</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Institution / Name</TableHead>
                <TableHead>Purpose / Scope</TableHead>
                <TableHead>Granted</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                consents!.map((c: any) => {
                  const institution = useMock ? c.institution : (c.name || c.institution || "—");
                  const purpose = useMock ? c.purpose : (c.scope || c.purpose || "—");
                  const granted = useMock ? c.grantedDate : (c.grantedDate || (c.granted ? "Yes" : "No"));
                  const expires = useMock ? c.expiryDate : (c.expiryDate || c.expires_at || "—");
                  const status = useMock ? c.status : (c.revoked_at ? "revoked" : c.status || "active");

                  return (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-sm">{institution}</TableCell>
                      <TableCell className="text-sm">{purpose}</TableCell>
                      <TableCell className="text-sm">{granted}</TableCell>
                      <TableCell className="text-sm">{expires}</TableCell>
                      <TableCell><Badge variant="outline" className={getConsentStatusColor(status)}>{status}</Badge></TableCell>
                      <TableCell className="text-right">
                        {(status === "active" || c.granted) && !useMock && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-600"
                            disabled={revokeMutation.isPending}
                            onClick={() => revokeMutation.mutate(c.id)}
                          >
                            {revokeMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <XCircle className="h-3.5 w-3.5 mr-1" />}
                            Revoke
                          </Button>
                        )}
                        {useMock && status === "active" && (
                          <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-600" disabled>
                            <XCircle className="h-3.5 w-3.5 mr-1" /> Revoke
                          </Button>
                        )}
                      </TableCell>
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
