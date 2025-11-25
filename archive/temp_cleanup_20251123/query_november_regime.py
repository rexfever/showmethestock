#!/usr/bin/env python3
"""
11월 장세 데이터 DB 조회 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def query_november_regime():
    """DB에서 11월 장세 데이터 조회"""
    print("=== 11월 장세 데이터 DB 조회 ===\n")
    
    try:
        from db_manager import db_manager
        import json
        
        # 11월 데이터 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, final_regime, kr_sentiment, us_prev_sentiment, 
                       us_preopen_sentiment, kr_metrics, us_metrics, version
                FROM market_regime_daily 
                WHERE date >= '2025-11-01' AND date <= '2025-11-30'
                ORDER BY date
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("❌ 11월 장세 데이터가 없습니다.")
                return
            
            print(f"📊 총 {len(rows)}개의 장세 데이터를 찾았습니다.\n")
            
            # 헤더 출력
            print("-" * 120)
            print(f"{'날짜':>10} | {'최종레짐':>8} | {'한국레짐':>8} | {'미국레짐':>8} | {'Pre-open':>8} | {'한국점수':>8} | {'미국점수':>8} | {'버전':>8}")
            print("-" * 120)
            
            regime_counts = {"bull": 0, "neutral": 0, "bear": 0, "crash": 0}
            
            for row in rows:
                date = row['date'].strftime('%Y-%m-%d')
                final_regime = row['final_regime']
                kr_regime = row['kr_sentiment']
                us_regime = row['us_prev_sentiment']
                preopen = row['us_preopen_sentiment']
                version = row['version']
                
                # 점수 추출
                kr_score = 0.0
                us_score = 0.0
                
                try:
                    if row['kr_metrics']:
                        kr_metrics = json.loads(row['kr_metrics'])
                        kr_score = kr_metrics.get('kr_score', 0.0)
                except:
                    pass
                
                try:
                    if row['us_metrics']:
                        us_metrics = json.loads(row['us_metrics'])
                        # us_prev_score 찾기
                        for key in ['us_prev_score', 'us_score', 'score']:
                            if key in us_metrics:
                                us_score = us_metrics[key]
                                break
                except:
                    pass
                
                # 카운트 업데이트
                regime_counts[final_regime] += 1
                
                # 출력
                print(f"{date} | {final_regime:>8} | {kr_regime:>8} | {us_regime:>8} | "
                      f"{preopen:>8} | {kr_score:>8.2f} | {us_score:>8.2f} | {version:>8}")
            
            print("-" * 120)
            
            # 요약 통계
            total_days = len(rows)
            print(f"\n=== 11월 장세 요약 ===")
            print(f"총 데이터: {total_days}일")
            print(f"강세장(bull): {regime_counts['bull']}일 ({regime_counts['bull']/total_days*100:.1f}%)")
            print(f"중립장(neutral): {regime_counts['neutral']}일 ({regime_counts['neutral']/total_days*100:.1f}%)")
            print(f"약세장(bear): {regime_counts['bear']}일 ({regime_counts['bear']/total_days*100:.1f}%)")
            print(f"급락장(crash): {regime_counts['crash']}일 ({regime_counts['crash']/total_days*100:.1f}%)")
            
            # 레짐 변화 분석
            print(f"\n=== 레짐 변화 패턴 ===")
            regime_changes = 0
            prev_regime = None
            
            for row in rows:
                current_regime = row['final_regime']
                if prev_regime and current_regime != prev_regime:
                    regime_changes += 1
                    date_str = row['date'].strftime('%Y-%m-%d')
                    print(f"{date_str}: {prev_regime} → {current_regime}")
                prev_regime = current_regime
            
            print(f"총 레짐 변화: {regime_changes}회")
            
            # 한국 vs 미국 레짐 비교
            print(f"\n=== 한국 vs 미국 레짐 비교 ===")
            agreement = 0
            for row in rows:
                if row['kr_sentiment'] == row['us_prev_sentiment']:
                    agreement += 1
            
            print(f"한국-미국 레짐 일치율: {agreement/total_days*100:.1f}% ({agreement}/{total_days})")
            
            # 버전별 분포
            version_counts = {}
            for row in rows:
                version = row['version']
                version_counts[version] = version_counts.get(version, 0) + 1
            
            print(f"\n=== 버전별 분포 ===")
            for version, count in version_counts.items():
                print(f"{version}: {count}일 ({count/total_days*100:.1f}%)")
            
    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query_november_regime()