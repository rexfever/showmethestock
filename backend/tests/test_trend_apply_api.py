"""
추세 변동 대응 API 테스트
.env 파일 파싱 및 업데이트 로직 테스트
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTrendApplyAPI(unittest.TestCase):
    """추세 변동 대응 API 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_dir = tempfile.mkdtemp()
        self.test_env_path = os.path.join(self.test_dir, ".env")
        
    def tearDown(self):
        """테스트 정리"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_test_env_file(self, content):
        """테스트용 .env 파일 생성"""
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return self.test_env_path
    
    def test_env_file_parsing_basic(self):
        """기본 .env 파일 파싱 테스트"""
        content = """# 주석 라인
MIN_SIGNALS=5
RSI_UPPER_LIMIT=60
VOL_MA5_MULT=2.2
GAP_MAX=0.008
EXT_FROM_TEMA20_MAX=0.008
OTHER_KEY=other_value
"""
        self.create_test_env_file(content)
        
        # 파싱 로직 테스트
        env_dict = {}
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # 검증
        self.assertEqual(env_dict["MIN_SIGNALS"], "5")
        self.assertEqual(env_dict["RSI_UPPER_LIMIT"], "60")
        self.assertEqual(env_dict["VOL_MA5_MULT"], "2.2")
        self.assertEqual(env_dict["GAP_MAX"], "0.008")
        self.assertEqual(env_dict["EXT_FROM_TEMA20_MAX"], "0.008")
        self.assertEqual(env_dict["OTHER_KEY"], "other_value")
        self.assertNotIn("#", env_dict)  # 주석 제외 확인
    
    def test_env_file_parsing_with_comments(self):
        """주석이 포함된 .env 파일 파싱 테스트"""
        content = """MIN_SIGNALS=5  # 이것은 주석
RSI_UPPER_LIMIT=60
# 전체 라인 주석
VOL_MA5_MULT=2.2
"""
        self.create_test_env_file(content)
        
        env_dict = {}
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # 주석 제거
                if '#' in line:
                    line = line.split('#')[0].strip()
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key:
                    env_dict[key] = value
        
        # 검증
        self.assertEqual(env_dict["MIN_SIGNALS"], "5")
        self.assertEqual(env_dict["RSI_UPPER_LIMIT"], "60")
        self.assertEqual(env_dict["VOL_MA5_MULT"], "2.2")
    
    def test_reverse_mapping_safety(self):
        """역매핑 안전성 테스트"""
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
            "vol_ma5_mult": "VOL_MA5_MULT",
            "gap_max": "GAP_MAX",
            "ext_from_tema20_max": "EXT_FROM_TEMA20_MAX",
        }
        
        # 역매핑 생성
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 검증
        self.assertEqual(reverse_mapping["MIN_SIGNALS"], "min_signals")
        self.assertEqual(reverse_mapping["RSI_UPPER_LIMIT"], "rsi_upper_limit")
        self.assertEqual(reverse_mapping["VOL_MA5_MULT"], "vol_ma5_mult")
        
        # 존재하지 않는 키 접근 테스트 (안전하게)
        result = reverse_mapping.get("NON_EXISTENT_KEY")
        self.assertIsNone(result)
        
        # next() 대신 get() 사용으로 예외 없음 확인
        param_key = reverse_mapping.get("MIN_SIGNALS")
        self.assertIsNotNone(param_key)
        self.assertEqual(param_key, "min_signals")
    
    def test_env_file_update_logic(self):
        """env 파일 업데이트 로직 테스트"""
        content = """MIN_SIGNALS=5
RSI_UPPER_LIMIT=60
VOL_MA5_MULT=2.2
GAP_MAX=0.008
EXT_FROM_TEMA20_MAX=0.008
OTHER_KEY=other_value
"""
        self.create_test_env_file(content)
        
        # 업데이트할 파라미터
        params = {
            "min_signals": "3",
            "rsi_upper_limit": "65",
            "vol_ma5_mult": "1.8"
        }
        
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
            "vol_ma5_mult": "VOL_MA5_MULT",
            "gap_max": "GAP_MAX",
            "ext_from_tema20_max": "EXT_FROM_TEMA20_MAX",
        }
        
        # .env 파일 읽기
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        # 역매핑 생성
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 업데이트 로직
        output_lines = []
        existing_keys = set()
        
        for line in env_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=')[0].strip()
                if key in reverse_mapping:
                    param_key = reverse_mapping.get(key)  # 안전하게 접근
                    if param_key and param_key in params:
                        output_lines.append(f"{key}={params[param_key]}\n")
                        existing_keys.add(key)
                    else:
                        output_lines.append(line)  # 기존 값 유지
                        existing_keys.add(key)
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)
        
        # 새로 추가해야 할 항목
        for param_key, env_key in param_mapping.items():
            if env_key not in existing_keys and param_key in params:
                output_lines.append(f"{env_key}={params[param_key]}\n")
        
        # 파일 쓰기
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        
        # 검증
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        self.assertIn("MIN_SIGNALS=3", updated_content)
        self.assertIn("RSI_UPPER_LIMIT=65", updated_content)
        self.assertIn("VOL_MA5_MULT=1.8", updated_content)
        self.assertIn("GAP_MAX=0.008", updated_content)  # 변경되지 않음
        self.assertIn("OTHER_KEY=other_value", updated_content)  # 다른 키 유지
    
    def test_env_file_update_new_key(self):
        """새로운 키 추가 테스트"""
        content = """OTHER_KEY=other_value
"""
        self.create_test_env_file(content)
        
        params = {
            "min_signals": "3",
            "rsi_upper_limit": "65"
        }
        
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
        }
        
        # .env 파일 읽기
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        # 역매핑 생성
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 업데이트 로직
        output_lines = []
        existing_keys = set()
        
        for line in env_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=')[0].strip()
                if key in reverse_mapping:
                    param_key = reverse_mapping.get(key)
                    if param_key and param_key in params:
                        output_lines.append(f"{key}={params[param_key]}\n")
                        existing_keys.add(key)
                    else:
                        output_lines.append(line)
                        existing_keys.add(key)
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)
        
        # 새로 추가해야 할 항목
        for param_key, env_key in param_mapping.items():
            if env_key not in existing_keys and param_key in params:
                output_lines.append(f"{env_key}={params[param_key]}\n")
        
        # 파일 쓰기
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        
        # 검증
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        self.assertIn("MIN_SIGNALS=3", updated_content)
        self.assertIn("RSI_UPPER_LIMIT=65", updated_content)
        self.assertIn("OTHER_KEY=other_value", updated_content)
    
    def test_reverse_mapping_no_stopiteration(self):
        """역매핑에서 StopIteration 예외 없음 확인"""
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
        }
        
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 존재하지 않는 키로 접근 (예외 없어야 함)
        non_existent_key = "NON_EXISTENT_KEY"
        
        # next() 사용 시 예외 발생 가능
        try:
            # 이 방법은 예외 발생 가능
            param_key = next(k for k, v in param_mapping.items() if v == non_existent_key)
            self.fail("StopIteration 예외가 발생해야 함")
        except StopIteration:
            pass  # 예상된 예외
        
        # get() 사용 시 예외 없음 (안전)
        param_key = reverse_mapping.get(non_existent_key)
        self.assertIsNone(param_key)
    
    def test_backup_creation(self):
        """백업 파일 생성 테스트"""
        content = "MIN_SIGNALS=5\n"
        self.create_test_env_file(content)
        
        # 백업 경로 생성
        backup_path = f"{self.test_env_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 백업 생성
        import shutil
        if os.path.exists(self.test_env_path):
            shutil.copy2(self.test_env_path, backup_path)
        
        # 검증
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        self.assertEqual(backup_content, content)
        
        # 정리
        if os.path.exists(backup_path):
            os.remove(backup_path)


class TestEnvFileEdgeCases(unittest.TestCase):
    """.env 파일 엣지 케이스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_dir = tempfile.mkdtemp()
        self.test_env_path = os.path.join(self.test_dir, ".env")
        
    def tearDown(self):
        """테스트 정리"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_empty_env_file(self):
        """빈 .env 파일 처리 테스트"""
        content = ""
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        env_dict = {}
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        self.assertEqual(len(env_dict), 0)
    
    def test_env_file_with_whitespace(self):
        """공백이 포함된 .env 파일 처리 테스트"""
        content = """  MIN_SIGNALS = 5  
RSI_UPPER_LIMIT=60
"""
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        env_dict = {}
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        self.assertEqual(env_dict["MIN_SIGNALS"], "5")
        self.assertEqual(env_dict["RSI_UPPER_LIMIT"], "60")
    
    def test_env_file_with_empty_values(self):
        """빈 값이 포함된 .env 파일 처리 테스트"""
        content = """MIN_SIGNALS=
RSI_UPPER_LIMIT=60
EMPTY_KEY=
"""
        with open(self.test_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        env_dict = {}
        with open(self.test_env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key:  # key가 비어있지 않은 경우만
                    env_dict[key] = value
        
        self.assertEqual(env_dict["MIN_SIGNALS"], "")
        self.assertEqual(env_dict["RSI_UPPER_LIMIT"], "60")
        self.assertEqual(env_dict["EMPTY_KEY"], "")


if __name__ == '__main__':
    unittest.main()


