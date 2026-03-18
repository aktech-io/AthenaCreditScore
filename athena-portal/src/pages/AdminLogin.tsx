import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, Eye, EyeOff, ArrowLeft, Lock, Server, BarChart3, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { adminLogin } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import heroDashboard from "@/assets/hero-dashboard.jpg";

export default function AdminLogin() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await adminLogin(username, password);
      login(res.token, res.roles);
      navigate("/admin");
    } catch (err: unknown) {
      toast({
        variant: "destructive",
        title: "Login failed",
        description: err instanceof Error ? err.message : "Invalid credentials",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <img
          src={heroDashboard}
          alt="Athena CRB"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/70 to-primary/90" />
        <div className="absolute inset-0 flex flex-col justify-between p-12 text-primary-foreground">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold text-lg">Athena</span>
              <span className="font-light ml-1 opacity-80">CRB</span>
            </div>
          </div>

          <div>
            <h2 className="text-4xl font-extrabold tracking-tight mb-4 leading-tight">
              Bureau Management<br />& Analytics
            </h2>
            <p className="text-lg opacity-80 max-w-md leading-relaxed mb-10">
              Access real-time credit bureau operations, portfolio analytics, and AI model configuration.
            </p>

            <div className="grid grid-cols-3 gap-4">
              {[
                { icon: Server, label: "System Uptime", value: "99.97%" },
                { icon: BarChart3, label: "Reports Today", value: "1,247" },
                { icon: Lock, label: "Security Level", value: "SOC-2" },
              ].map((stat) => (
                <div key={stat.label} className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
                  <stat.icon className="h-4 w-4 mb-2 opacity-70" />
                  <div className="text-xl font-bold font-mono">{stat.value}</div>
                  <div className="text-[11px] opacity-60">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs opacity-50">
            © 2025 Athena Credit Bureau · Licensed by CBK
          </p>
        </div>
      </div>

      {/* Right panel - login form */}
      <div className="flex-1 flex items-center justify-center bg-background p-6">
        <div className="absolute top-6 left-6 lg:hidden">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Link>
          </Button>
        </div>
        <div className="absolute top-6 right-6">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login">Client Portal →</Link>
          </Button>
        </div>

        <div className="w-full max-w-sm">
          <div className="text-center mb-8 lg:hidden">
            <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center mx-auto mb-4">
              <Shield className="h-7 w-7 text-primary-foreground" />
            </div>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Admin Portal</h1>
            <p className="text-sm text-muted-foreground mt-1">Sign in with your administrator credentials</p>
          </div>

          <Card className="border-border/50">
            <CardContent className="p-6">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="admin-username">Username</Label>
                  <Input id="admin-username" placeholder="admin" value={username} onChange={(e) => setUsername(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="admin-pass">Password</Label>
                  <div className="relative">
                    <Input
                      id="admin-pass"
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-10 w-10"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <Button type="submit" className="w-full shadow-lg shadow-primary/20" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Sign In to Admin Portal
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-xs text-muted-foreground mt-6">
            Default credentials: admin / admin
          </p>
        </div>
      </div>
    </div>
  );
}
