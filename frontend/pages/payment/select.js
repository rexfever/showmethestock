import { useState } from 'react';
import { useRouter } from 'next/router';

export default function PaymentSelect() {
    const router = useRouter();
    const { plan } = router.query;
    const [loading, setLoading] = useState(false);

    const handleKakaoPayment = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/payment/kakao/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ plan_id: plan })
            });

            const data = await response.json();
            if (data.payment_url) {
                window.location.href = data.payment_url;
            }
        } catch (error) {
            console.error('카카오페이 결제 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleNaverPayment = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/payment/naver/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ plan_id: plan })
            });

            const data = await response.json();
            if (data.payment_url) {
                window.location.href = data.payment_url;
            }
        } catch (error) {
            console.error('네이버페이 결제 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const handlePortOnePayment = async (payMethod) => {
        setLoading(true);
        try {
            const response = await fetch('/api/payment/portone/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ plan_id: plan, pay_method: payMethod })
            });

            const data = await response.json();
            if (data.payment_data) {
                // 포트원 결제창 호출
                window.IMP.request_pay(data.payment_data, (response) => {
                    if (response.success) {
                        // 결제 검증
                        fetch('/api/payment/portone/verify', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${localStorage.getItem('token')}`
                            },
                            body: JSON.stringify({
                                imp_uid: response.imp_uid,
                                merchant_uid: response.merchant_uid
                            })
                        }).then(() => {
                            router.push('/payment/success');
                        });
                    }
                });
            }
        } catch (error) {
            console.error('포트원 결제 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleTossPayment = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/payment/toss/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ plan_id: plan })
            });

            const data = await response.json();
            if (data.payment_data) {
                // 토스페이먼츠 결제창 호출
                window.TossPayments(process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY)
                    .requestPayment('CARD', data.payment_data)
                    .then((response) => {
                        // 결제 승인
                        fetch('/api/payment/toss/confirm', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${localStorage.getItem('token')}`
                            },
                            body: JSON.stringify({
                                payment_key: response.paymentKey,
                                order_id: response.orderId,
                                amount: response.amount
                            })
                        }).then(() => {
                            router.push('/payment/success');
                        });
                    });
            }
        } catch (error) {
            console.error('토스페이먼츠 결제 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 py-12">
            <div className="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
                <h1 className="text-2xl font-bold text-center mb-8">결제 방법 선택</h1>
                
                <div className="space-y-4">
                    <button
                        onClick={handleKakaoPayment}
                        disabled={loading}
                        className="w-full bg-yellow-400 hover:bg-yellow-500 text-black font-bold py-4 px-6 rounded-lg flex items-center justify-center space-x-2"
                    >
                        <span>카카오페이로 결제</span>
                    </button>

                    <button
                        onClick={handleNaverPayment}
                        disabled={loading}
                        className="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-6 rounded-lg flex items-center justify-center space-x-2"
                    >
                        <span>네이버페이로 결제</span>
                    </button>

                    <button
                        onClick={() => handlePortOnePayment('card')}
                        disabled={loading}
                        className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-4 px-6 rounded-lg flex items-center justify-center space-x-2"
                    >
                        <span>카드결제 (포트원)</span>
                    </button>

                    <button
                        onClick={handleTossPayment}
                        disabled={loading}
                        className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-4 px-6 rounded-lg flex items-center justify-center space-x-2"
                    >
                        <span>토스페이먼츠</span>
                    </button>
                </div>

                <div className="mt-6 text-center">
                    <button
                        onClick={() => router.back()}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        이전으로
                    </button>
                </div>
            </div>
        </div>
    );
}