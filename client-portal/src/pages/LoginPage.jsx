import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Phone, AlertCircle } from 'lucide-react';

const MOCK_JWT = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIrMjU0NzExMjIzMzQ0Iiwicm9sZXMiOlsiQ1VTVE9NRVIiXSwiY3VzdG9tZXJJZCI6MTAxfQ.mock';

export default function LoginPage() {
    const [step, setStep] = useState('PHONE'); // PHONE | OTP
    const [phone, setPhone] = useState('');
    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();
    const otpRefs = useRef([]);

    const handleRequestOtp = async (e) => {
        e.preventDefault();
        setError(''); setLoading(true);

        // Demo Backdoor for easy testing
        if (['1', '2', '3', '101'].includes(phone)) {
            const demoId = parseInt(phone, 10);
            try {
                const res = await api.demoToken(demoId);
                login(res.token, { phone: '+254700000000', customerId: demoId });
            } catch {
                login(MOCK_JWT, { phone: '+254700000000', customerId: demoId });
            }
            navigate('/');
            return;
        }

        try {
            await api.requestOtp(phone);
            setStep('OTP');
        } catch {
            // MVP: proceed to OTP step even without backend
            setStep('OTP');
        } finally { setLoading(false); }
    };

    const handleOtpChange = (i, val) => {
        const cleaned = val.replace(/\D/, '').slice(-1);
        const next = [...otp];
        next[i] = cleaned;
        setOtp(next);
        if (cleaned && i < 5) otpRefs.current[i + 1]?.focus();
    };

    const handleOtpKeyDown = (i, e) => {
        if (e.key === 'Backspace' && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
    };

    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        setError(''); setLoading(true);
        const code = otp.join('');
        try {
            const res = await api.verifyOtp(phone, code);
            login(res.token, { phone, customerId: res.customerId });
            navigate('/');
        } catch {
            // MVP: accept any 6-digit OTP entered
            if (code.length === 6) {
                login(MOCK_JWT, { phone, customerId: 101 });
                navigate('/');
            } else {
                setError('Please enter all 6 digits');
            }
        } finally { setLoading(false); }
    };

    return (
        <div className="client-login">
            <div className="client-login-card">
                <div style={{ textAlign: 'center', marginBottom: 28 }}>
                    <div style={{
                        width: 56, height: 56,
                        background: 'linear-gradient(135deg, var(--brand-500), var(--brand-700))',
                        borderRadius: 16, display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: 24,
                        margin: '0 auto 14px',
                        boxShadow: '0 8px 24px rgba(16,185,129,0.35)',
                    }}>✦</div>
                    <h2>My Athena Score</h2>
                    <p style={{ marginTop: 8, fontSize: '0.875rem' }}>
                        {step === 'PHONE'
                            ? 'Enter your phone number to receive a one-time code'
                            : `We sent a 6-digit code to ${phone}`}
                    </p>
                </div>

                {error && (
                    <div style={{
                        background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.25)',
                        borderRadius: 10, padding: '10px 14px', display: 'flex', alignItems: 'center',
                        gap: 8, color: 'var(--red-400)', fontSize: '0.85rem', marginBottom: 16,
                    }}>
                        <AlertCircle size={14} /> {error}
                    </div>
                )}

                {step === 'PHONE' ? (
                    <form onSubmit={handleRequestOtp}>
                        <div className="form-group">
                            <label className="form-label">Phone Number</label>
                            <div style={{ position: 'relative' }}>
                                <Phone size={14} style={{
                                    position: 'absolute', left: 12, top: '50%',
                                    transform: 'translateY(-50%)', color: 'var(--gray-500)',
                                }} />
                                <input
                                    id="phone"
                                    type="tel"
                                    className="form-input w-full"
                                    style={{ paddingLeft: 36 }}
                                    placeholder="+254 7XX XXX XXX"
                                    value={phone}
                                    onChange={e => setPhone(e.target.value)}
                                    required autoFocus
                                />
                            </div>
                        </div>
                        <button type="submit" className="btn btn-primary w-full"
                            style={{ justifyContent: 'center', marginTop: 6 }} disabled={loading}>
                            {loading ? 'Sending code…' : 'Send OTP'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleVerifyOtp}>
                        <div className="otp-grid">
                            {otp.map((digit, i) => (
                                <input
                                    key={i}
                                    id={`otp-${i}`}
                                    ref={el => otpRefs.current[i] = el}
                                    className="otp-box"
                                    type="text" inputMode="numeric"
                                    maxLength={1}
                                    value={digit}
                                    onChange={e => handleOtpChange(i, e.target.value)}
                                    onKeyDown={e => handleOtpKeyDown(i, e)}
                                    autoFocus={i === 0}
                                />
                            ))}
                        </div>
                        <button type="submit" className="btn btn-primary w-full"
                            style={{ justifyContent: 'center' }} disabled={loading}>
                            {loading ? 'Verifying…' : 'Verify & Sign In'}
                        </button>
                        <button
                            type="button" className="btn btn-ghost w-full"
                            style={{ justifyContent: 'center', marginTop: 10 }}
                            onClick={() => { setStep('PHONE'); setOtp(['', '', '', '', '', '']); setError(''); }}
                        >
                            ← Change number
                        </button>
                    </form>
                )}

                <p style={{ textAlign: 'center', marginTop: 20, fontSize: '0.72rem', color: 'var(--gray-600)' }}>
                    Your data is encrypted and never shared without consent.
                </p>
            </div>
        </div>
    );
}
