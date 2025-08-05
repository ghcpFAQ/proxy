"""
JSON解析模块 - 处理JSON数据的解析、解压缩和清理
"""
import json
import gzip
import zlib
import base64
import urllib.parse
from mitmproxy import ctx

class JSONParser:
    """JSON解析器，处理各种格式的JSON数据"""
    
    def __init__(self):
        pass
    
    async def split_jsons(self, json_string, url=""):
        """
        利用mitmproxy功能改进的JSON分割方法，更好地处理各种数据格式
        """
        json_objects = []
        
        # 首先检查输入是否为空或只包含空白字符
        if not json_string or not json_string.strip():
            return json_objects
        
        # 记录原始数据的基本信息
        ctx.log.debug(f"split_jsons 原始输入长度: {len(json_string)}")
        
        # 优先使用解压缩后的内容
        processed_data = self._get_decoded_content(json_string)
        if processed_data != json_string:
            ctx.log.debug(f"解压缩后长度: {len(processed_data)}")
            json_string = processed_data
        
        # 尝试处理可能的编码数据
        processed_data = self._try_decode_data(json_string)
        if processed_data != json_string:
            ctx.log.debug(f"数据解码后长度: {len(processed_data)}")
            json_string = processed_data
        
        # 检查是否包含明显的二进制数据
        if self._contains_binary_data(json_string):
            ctx.log.debug(f"检测到二进制数据，尝试其他处理方式")
            # 对于遥测数据，可能是特殊格式，先记录但不完全跳过
            if "telemetry" in url:
                ctx.log.debug("遥测数据可能使用特殊编码格式，尝试其他解析方法")
            return json_objects
        
        # 清理输入字符串
        cleaned_string = self._clean_json_string(json_string)
        if not cleaned_string:
            ctx.log.debug("清理后的字符串为空，跳过解析")
            return json_objects
        
        # 记录调试信息，但限制长度避免日志过长
        debug_string = cleaned_string[:200] + "..." if len(cleaned_string) > 200 else cleaned_string
        ctx.log.debug(f"split_jsons 清理后长度: {len(cleaned_string)}, 前200字符: {debug_string}")
        
        # 方法1: 尝试直接解析整个字符串作为单个JSON
        try:
            json_obj = json.loads(cleaned_string.strip())
            json_objects.append(json_obj)
            ctx.log.debug("成功解析为单个JSON对象")
            return json_objects
        except json.JSONDecodeError:
            pass
        
        # 方法1.5: 尝试解析为JSON数组（处理 [obj1,obj2,obj3] 格式）
        try:
            # 检查是否是数组格式
            if cleaned_string.strip().startswith('[') and cleaned_string.strip().endswith(']'):
                json_array = json.loads(cleaned_string.strip())
                if isinstance(json_array, list):
                    json_objects.extend(json_array)
                    ctx.log.debug(f"成功解析为JSON数组，包含{len(json_array)}个对象")
                    return json_objects
        except json.JSONDecodeError:
            pass
        
        # 方法2: 尝试按行分割，每行可能是一个JSON对象
        lines = cleaned_string.strip().split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 2:  # 跳过太短的行
                continue
            
            # 检查行是否看起来像JSON（以{开头，以}结尾）
            if not (line.startswith('{') and line.endswith('}')):
                continue
                
            try:
                json_obj = json.loads(line)
                json_objects.append(json_obj)
                ctx.log.debug(f"第{line_num+1}行解析成功")
            except json.JSONDecodeError as e:
                # 只记录看起来像JSON但解析失败的情况
                if line.startswith('{') and line.endswith('}'):
                    ctx.log.debug(f"第{line_num+1}行解析失败: {str(e)[:50]}...")
                continue
        
        # 如果按行解析成功了，返回结果
        if json_objects:
            ctx.log.debug(f"按行解析成功，共{len(json_objects)}个JSON对象")
            return json_objects
        
        # 方法3: 尝试将连续的JSON对象转换为有效的JSON数组格式
        # 处理 {obj1}{obj2}{obj3} 这种连续JSON对象的情况
        if self._looks_like_consecutive_json_objects(cleaned_string):
            try:
                # 尝试将连续的JSON对象包装成数组
                wrapped_json = self._wrap_consecutive_json_objects(cleaned_string)
                if wrapped_json:
                    json_array = json.loads(wrapped_json)
                    if isinstance(json_array, list):
                        json_objects.extend(json_array)
                        ctx.log.debug(f"成功将连续JSON对象转换为数组，包含{len(json_array)}个对象")
                        return json_objects
            except Exception as e:
                ctx.log.debug(f"连续JSON对象转换失败: {str(e)[:50]}...")
        
        # 方法4: 改进的括号匹配方法（仅在有效数据时）
        if self._looks_like_json(cleaned_string):
            try:
                json_objects = self._parse_json_with_bracket_matching(cleaned_string)
                if json_objects:
                    ctx.log.debug(f"括号匹配解析成功，共{len(json_objects)}个JSON对象")
                    return json_objects
            except Exception as e:
                ctx.log.debug(f"括号匹配解析失败: {str(e)[:50]}...")
        
        # 如果没有找到有效的JSON，记录但不作为错误
        if not json_objects:
            ctx.log.debug("未找到有效的JSON数据，可能是特殊编码格式或非JSON内容")
        
        return json_objects
    
    def _get_decoded_content(self, raw_content):
        """简化版本：优先尝试手动解压缩"""
        # 直接尝试手动解压缩作为备选方案
        return self._try_decompress_data(raw_content)
    
    def _try_decompress_data(self, data_string):
        """尝试解压缩可能压缩的数据"""
        if isinstance(data_string, str):
            try:
                data_bytes = data_string.encode('utf-8')
            except UnicodeEncodeError:
                return data_string
        else:
            data_bytes = data_string
        
        # 尝试gzip解压缩
        try:
            # 检查是否是gzip格式（magic number: 1f 8b）
            if len(data_bytes) >= 2 and data_bytes[:2] == b'\x1f\x8b':
                decompressed = gzip.decompress(data_bytes)
                decoded = decompressed.decode('utf-8', errors='ignore')
                ctx.log.debug("成功进行gzip解压缩")
                return decoded
        except Exception:
            pass
        
        # 尝试zlib解压缩
        try:
            decompressed = zlib.decompress(data_bytes)
            decoded = decompressed.decode('utf-8', errors='ignore')
            ctx.log.debug("成功进行zlib解压缩")
            return decoded
        except Exception:
            pass
        
        # 如果是字节数据，尝试直接解码
        if isinstance(data_string, bytes):
            try:
                return data_string.decode('utf-8', errors='ignore')
            except:
                pass
        
        # 如果所有解压缩都失败，返回原始数据
        return data_string
    
    def _try_decode_data(self, data_string):
        """尝试解码可能编码的数据"""
        try:
            # 尝试base64解码
            if len(data_string) % 4 == 0:  # base64数据长度应该是4的倍数
                try:
                    decoded = base64.b64decode(data_string).decode('utf-8')
                    if self._looks_like_json(decoded):
                        ctx.log.debug("成功进行base64解码")
                        return decoded
                except:
                    pass
        except:
            pass
        
        try:
            # 尝试URL解码
            decoded = urllib.parse.unquote(data_string)
            if decoded != data_string and self._looks_like_json(decoded):
                ctx.log.debug("成功进行URL解码")
                return decoded
        except:
            pass
        
        # 如果所有解码都失败，返回原始数据
        return data_string
    
    def _contains_binary_data(self, data_string):
        """检查字符串是否包含二进制数据"""
        try:
            # 尝试编码为UTF-8，如果失败则可能是二进制数据
            data_string.encode('utf-8')
            
            # 检查是否包含大量不可打印字符
            printable_chars = sum(1 for c in data_string if c.isprintable() or c.isspace())
            total_chars = len(data_string)
            
            if total_chars == 0:
                return False
                
            printable_ratio = printable_chars / total_chars
            
            # 如果可打印字符比例低于70%，认为是二进制数据
            return printable_ratio < 0.7
            
        except UnicodeEncodeError:
            return True
    
    def _clean_json_string(self, json_string):
        """清理JSON字符串，移除无效字符"""
        try:
            # 移除控制字符，但保留换行符、制表符等
            cleaned = ''.join(char for char in json_string 
                            if char.isprintable() or char in '\n\r\t ')
            
            # 移除多余的空白字符
            lines = cleaned.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            
            return '\n'.join(cleaned_lines) if cleaned_lines else ''
            
        except Exception:
            return ''
    
    def _looks_like_json(self, data_string):
        """检查字符串是否看起来像JSON"""
        stripped = data_string.strip()
        
        # 基本检查：JSON应该以{或[开头
        if not stripped:
            return False
            
        # 检查是否包含JSON的基本特征
        json_indicators = ['{', '}', '"', ':']
        return any(indicator in stripped for indicator in json_indicators)
    
    def _looks_like_consecutive_json_objects(self, data_string):
        """检查字符串是否看起来像连续的JSON对象 {obj1}{obj2}{obj3}"""
        stripped = data_string.strip()
        
        # 基本检查
        if not stripped.startswith('{'):
            return False
        
        # 计算 { 和 } 的数量，如果 { 的数量大于1，可能是连续的JSON对象
        open_braces = stripped.count('{')
        close_braces = stripped.count('}')
        
        # 连续JSON对象的特征：
        # 1. 有多个开括号
        # 2. 括号数量相等
        # 3. 不是标准的JSON数组格式
        return (open_braces > 1 and 
                open_braces == close_braces and 
                not (stripped.startswith('[') and stripped.endswith(']')))
    
    def _wrap_consecutive_json_objects(self, data_string):
        """将连续的JSON对象包装成JSON数组格式"""
        try:
            # 使用括号匹配来分离各个JSON对象
            objects = []
            depth = 0
            start_index = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(data_string):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if in_string:
                    continue
                    
                if char == '{':
                    if depth == 0:
                        start_index = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end_index = i + 1
                        json_str = data_string[start_index:end_index].strip()
                        if json_str and len(json_str) > 2:  # 至少要有{}
                            # 验证这是一个有效的JSON对象
                            try:
                                json.loads(json_str)  # 只是验证，不保存结果
                                objects.append(json_str)
                            except json.JSONDecodeError:
                                continue
            
            # 如果找到了多个有效的JSON对象，将它们包装成数组
            if len(objects) > 1:
                wrapped = '[' + ','.join(objects) + ']'
                ctx.log.debug(f"包装了{len(objects)}个连续JSON对象为数组")
                return wrapped
            elif len(objects) == 1:
                # 如果只有一个对象，直接返回
                return objects[0]
                
        except Exception as e:
            ctx.log.debug(f"包装连续JSON对象时出错: {str(e)[:50]}...")
        
        return None
    
    def _parse_json_with_bracket_matching(self, json_string):
        """使用改进的括号匹配算法解析JSON"""
        json_objects = []
        depth = 0
        start_index = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_string):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if in_string:
                continue
                
            if char == '{':
                if depth == 0:
                    start_index = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end_index = i + 1
                    try:
                        json_str = json_string[start_index:end_index].strip()
                        if json_str and len(json_str) > 2:  # 至少要有{}
                            json_obj = json.loads(json_str)
                            json_objects.append(json_obj)
                    except json.JSONDecodeError as e:
                        ctx.log.debug(f"括号匹配中JSON解析错误: {str(e)[:50]}...")
                        continue
                    except Exception as e:
                        ctx.log.debug(f"括号匹配中其他错误: {str(e)[:50]}...")
                        continue
        
        return json_objects

    async def parse_res_content(self, content):
        """解析响应内容，提取流式数据中的内容"""
        lines = content.strip().split('\n')
        # Initialize an empty string to collect all 'content' values
        content_string = ""

        for line in lines:
            # Remove the "data: " prefix and any trailing commas
            json_str = line.replace("data: ", "").rstrip(',')
            # Skip lines that do not contain JSON data
            if json_str == "[DONE]":
                continue
            # Parse the JSON data
            try:
                data_entry = json.loads(json_str)
                # Check if 'choices' is not empty
                if data_entry['choices']:
                    # Check if 'delta' and 'content' keys exist and 'content' is not None
                    if 'delta' in data_entry['choices'][0] and data_entry['choices'][0]['delta'].get('content') is not None:
                        # Concatenate the 'content' value to the content_string
                        content_string += data_entry['choices'][0]['delta']['content']
                    elif 'text' in data_entry['choices'][0]:
                        content_string += data_entry['choices'][0]['text']
            except json.JSONDecodeError as e:
                continue  # Continue with the next line

        ctx.log.debug("content_string: " + content_string)
        return content_string
