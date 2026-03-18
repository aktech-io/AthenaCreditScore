import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { requestOtp, verifyOtp } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Login() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { login } = useAuth();
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("0716360155");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await requestOtp(phone);
      toast({ title: "OTP Sent", description: "Check your phone for the verification code." });
      setStep("otp");
    } catch (err: unknown) {
      toast({
        variant: "destructive",
        title: "Failed to send OTP",
        description: err instanceof Error ? err.message : "Please try again",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await verifyOtp(phone, otp);
      login(res.token, ["CUSTOMER"], res.customerId);
      navigate("/client");
    } catch (err: unknown) {
      toast({
        variant: "destructive",
        title: "Verification failed",
        description: err instanceof Error ? err.message : "Invalid OTP",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="absolute top-6 left-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Link>
        </Button>
      </div>

      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mx-auto mb-4">
            <Shield className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Welcome to Athena CRB</h1>
          <p className="text-sm text-muted-foreground mt-1">Sign in to access your portal</p>
        </div>

        <Card className="border-border/50">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Client Sign In</CardTitle>
            <CardDescription>
              {step === "phone"
                ? "Enter your phone number to receive a one-time password"
                : "Enter the OTP sent to your phone"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "phone" ? (
              <form onSubmit={handleRequestOtp} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="client-phone">Phone Number</Label>
                  <Input
                    id="client-phone"
                    placeholder="0716360155"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
                <Button type="submit" className="w-full shadow-lg shadow-primary/20" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Send OTP
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="client-otp">Verification Code</Label>
                  <Input
                    id="client-otp"
                    placeholder="Enter OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    autoFocus
                  />
                </div>
                <Button type="submit" className="w-full shadow-lg shadow-primary/20" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Verify & Sign In
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full"
                  onClick={() => { setStep("phone"); setOtp(""); }}
                >
                  Change phone number
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        <div className="text-center mt-4">
          <Link to="/admin-login" className="text-xs text-muted-foreground hover:text-primary transition-colors">
            Admin? Sign in here →
          </Link>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Demo phone: 0716360155
        </p>
      </div>
    </div>
  );
}
