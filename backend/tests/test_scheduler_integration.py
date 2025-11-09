"""
스케줄러 통합 테스트
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduler import run_validation, run_market_analysis, setup_scheduler
import schedule


def test_scheduler_functions():
    """스케줄러 함수 테스트"""
    print("\n" + "="*80)
    print("스케줄러 통합 테스트")
    print("="*80)
    
    # 1. run_validation 테스트
    print("\n[1] run_validation 함수 테스트")
    try:
        run_validation()
        print("   ✅ run_validation 실행 성공")
    except Exception as e:
        print(f"   ❌ run_validation 실행 실패: {e}")
    
    # 2. run_market_analysis 테스트
    print("\n[2] run_market_analysis 함수 테스트")
    try:
        run_market_analysis()
        print("   ✅ run_market_analysis 실행 성공")
    except Exception as e:
        print(f"   ❌ run_market_analysis 실행 실패: {e}")
    
    # 3. setup_scheduler 테스트
    print("\n[3] setup_scheduler 함수 테스트")
    try:
        setup_scheduler()
        print("   ✅ setup_scheduler 실행 성공")
        
        # 등록된 작업 확인
        jobs = schedule.get_jobs()
        print(f"\n   📋 등록된 작업 수: {len(jobs)}")
        
        # 작업 목록 출력
        validation_jobs = [j for j in jobs if 'run_validation' in str(j.job_func)]
        market_jobs = [j for j in jobs if 'run_market_analysis' in str(j.job_func)]
        scan_jobs = [j for j in jobs if 'run_scan' in str(j.job_func)]
        
        print(f"   - 검증 작업 (15:31~15:40): {len(validation_jobs)}개")
        print(f"   - 장세 분석 작업 (15:40): {len(market_jobs)}개")
        print(f"   - 스캔 작업 (15:42): {len(scan_jobs)}개")
        
        # 작업 상세 출력 (처음 5개만)
        print(f"\n   📝 작업 상세 (처음 5개):")
        for i, job in enumerate(jobs[:5]):
            print(f"      {i+1}. {job}")
        
        if len(jobs) > 5:
            print(f"      ... 외 {len(jobs) - 5}개")
        
    except Exception as e:
        print(f"   ❌ setup_scheduler 실행 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ 스케줄러 통합 테스트 완료")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_scheduler_functions()

