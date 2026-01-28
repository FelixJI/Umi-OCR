"""
PaddleOCR 模型下载配置模块

按照功能渐进的方式组织模型下载选项，分为多个预设组合。
注意：此配置仅包含服务端模型，不包含移动端模型。

模型类别：
- 核心OCR: 文本检测、文本识别、方向分类
- 图像预处理: 文档方向分类、文档图像矫正
- 版面分析: 通用版面、表格区域、英文版面、子区域检测
- 表格识别: 表格结构、单元格检测、表格分类
- 公式识别: LaTeX公式识别
- 文档理解: Doc VLM文档视觉语言模型
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class ModelCategory(str, Enum):
    """模型类别枚举"""

    TEXT_DETECTION = "text_detection"
    TEXT_RECOGNITION = "text_recognition"
    TEXT_ORIENTATION = "text_orientation"
    DOC_ORIENTATION = "doc_orientation"
    DOC_UNWARPING = "doc_unwarping"
    LAYOUT_DETECTION = "layout_detection"
    LAYOUT_BLOCK = "layout_block"  # 子区域检测
    TABLE_STRUCTURE = "table_structure"
    TABLE_CELLS = "table_cells"
    TABLE_CLASSIFICATION = "table_classification"
    FORMULA_RECOGNITION = "formula_recognition"
    DOC_VLM = "doc_vlm"  # PP-DocBee文档理解模型
    OCR_VL = "ocr_vl"  # PaddleOCR-VL文档解析模型


@dataclass
class ModelInfo:
    """单个模型信息"""

    name: str  # 模型标识名称
    display_name: str  # 显示名称
    category: ModelCategory  # 模型类别
    size_mb: float  # 模型大小(MB)
    description: str  # 模型描述
    download_url: str  # 下载URL
    language: str = "ch"  # 语言: ch(中文), en(英文), multilingual(多语言)


@dataclass
class ModelPreset:
    """模型预设组合"""

    id: str
    name: str
    description: str
    models: List[str]  # 包含的模型ID列表
    total_size_mb: float  # 总大小
    recommended_for: str  # 推荐使用场景


# ============================================================================
# 核心OCR模型 - PP-OCRv5 (已移除v4过时模型)
# ============================================================================

# 文本检测模型
TEXT_DETECTION_MODELS = {
    "ppocrv5_server_det": ModelInfo(
        name="PP-OCRv5_server_det",
        display_name="PP-OCRv5 服务端检测模型",
        category=ModelCategory.TEXT_DETECTION,
        size_mb=101.0,
        description="最新高精度检测模型，Hmean 83.8%，支持109种语言",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar",
        language="multilingual",
    ),
    "ppocrv5_mobile_det": ModelInfo(
        name="PP-OCRv5_mobile_det",
        display_name="PP-OCRv5 移动端检测模型",
        category=ModelCategory.TEXT_DETECTION,
        size_mb=4.7,
        description="轻量检测模型，适合端侧部署，Hmean 79.0%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_det_infer.tar",
        language="multilingual",
    ),
}

# 文本识别模型
TEXT_RECOGNITION_MODELS = {
    "ppocrv5_server_rec": ModelInfo(
        name="PP-OCRv5_server_rec",
        display_name="PP-OCRv5 服务端识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=81.0,
        description="单模型支持简中/繁中/英/日/拼音，精度86.38%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_rec_infer.tar",
        language="multilingual",
    ),
    "ppocrv5_mobile_rec": ModelInfo(
        name="PP-OCRv5_mobile_rec",
        display_name="PP-OCRv5 移动端识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=16.0,
        description="轻量识别模型，精度81.29%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_rec_infer.tar",
        language="multilingual",
    ),
}

# ============================================================================
# 多语言V5识别模型 - 可选下载项
# ============================================================================

MULTILANGUAGE_RECOGNITION_MODELS = {
    # 语言组模型
    "cyrillic_ppocrv5_rec": ModelInfo(
        name="cyrillic_PP-OCRv5_mobile_rec",
        display_name="西里尔字母识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="支持俄语、乌克兰语、白俄罗斯语等20+种语言",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/cyrillic_PP-OCRv5_mobile_rec_infer.tar",
        language="cyrillic",
    ),
    "latin_ppocrv5_rec": ModelInfo(
        name="latin_PP-OCRv5_mobile_rec",
        display_name="拉丁语系识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="支持法文、德文、西语、37+种语言",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/latin_PP-OCRv5_mobile_rec_infer.tar",
        language="latin",
    ),
    "arabic_ppocrv5_rec": ModelInfo(
        name="arabic_PP-OCRv5_mobile_rec",
        display_name="阿拉伯语系识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="支持阿拉伯语、波斯语、20+种语言",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/arabic_PP-OCRv5_mobile_rec_infer.tar",
        language="arabic",
    ),
    "devanagari_ppocrv5_rec": ModelInfo(
        name="devanagari_PP-OCRv5_mobile_rec",
        display_name="天城文识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="支持印地语、马拉地语、10+种语言",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/devanagari_PP-OCRv5_mobile_rec_infer.tar",
        language="devanagari",
    ),
    # 语言专用模型
    "korean_ppocrv5_rec": ModelInfo(
        name="korean_PP-OCRv5_mobile_rec",
        display_name="韩语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="韩语专用优化模型",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/korean_PP-OCRv5_mobile_rec_infer.tar",
        language="korean",
    ),
    "japan_ppocrv5_rec": ModelInfo(
        name="japan_PP-OCRv5_mobile_rec",
        display_name="日语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="日语专用优化模型",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/japan_PP-OCRv5_mobile_rec_infer.tar",
        language="japan",
    ),
    "th_ppocrv5_rec": ModelInfo(
        name="th_PP-OCRv5_mobile_rec",
        display_name="泰语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="泰语专用，精度82.68%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/th_PP-OCRv5_mobile_rec_infer.tar",
        language="th",
    ),
    "el_ppocrv5_rec": ModelInfo(
        name="el_PP-OCRv5_mobile_rec",
        display_name="希腊语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="希腊语专用，精度89.28%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/el_PP-OCRv5_mobile_rec_infer.tar",
        language="el",
    ),
    "ta_ppocrv5_rec": ModelInfo(
        name="ta_PP-OCRv5_mobile_rec",
        display_name="泰米尔语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="泰米尔语专用，精度94.2%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/ta_PP-OCRv5_mobile_rec_infer.tar",
        language="ta",
    ),
    "te_ppocrv5_rec": ModelInfo(
        name="te_PP-OCRv5_mobile_rec",
        display_name="泰卢固语识别模型",
        category=ModelCategory.TEXT_RECOGNITION,
        size_mb=8.0,
        description="泰卢固语专用，精度87.65%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/te_PP-OCRv5_mobile_rec_infer.tar",
        language="te",
    ),
}

# 方向分类模型
ORIENTATION_MODELS = {
    "pp_lcnet_doc_ori": ModelInfo(
        name="PP-LCNet_x1_0_doc_ori",
        display_name="文档方向分类模型",
        category=ModelCategory.DOC_ORIENTATION,
        size_mb=7.0,
        description="文档图像方向分类，支持0°/90°/180°/270°旋转校正",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar",
    ),
    "pp_lcnet_textline_ori": ModelInfo(
        name="PP-LCNet_x1_0_textline_ori",
        display_name="文本行方向分类模型",
        category=ModelCategory.TEXT_ORIENTATION,
        size_mb=7.0,
        description="文本行方向分类，检测水平/垂直文本",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar",
    ),
}

# 图像预处理模型 - 文档矫正
DOC_UNWARPING_MODELS = {
    "uvdoc": ModelInfo(
        name="UVDoc",
        display_name="文档图像矫正模型",
        category=ModelCategory.DOC_UNWARPING,
        size_mb=30.3,
        description="弯曲文档图像矫正，用于处理透视变换和曲面文档",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UVDoc_infer.tar",
    ),
}

# ============================================================================
# 版面分析模型
# ============================================================================

# 通用版面分析模型 - 23类区域
LAYOUT_DETECTION_MODELS = {
    "pp_doclayout_plus_l": ModelInfo(
        name="PP-DocLayout_plus-L",
        display_name="PP-DocLayout+ L版面分析模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=126.0,
        description="最新高精度版面分析，支持20类区域：文档标题、段落标题、文本、页码、摘要、目录、参考文献、脚注、页眉、页脚、算法、公式、公式编号、图像、表格、图和表标题、印章、图表、侧栏文本和参考文献内容",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout_plus-L_infer.tar",
    ),
    "pp_doclayout_l": ModelInfo(
        name="PP-DocLayout-L",
        display_name="PP-DocLayout L版面分析模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=123.8,
        description="高精度版面分析，支持23类区域：文档标题、段落标题、文本、页码、摘要、目录、参考文献、脚注、页眉、页脚、算法、公式、公式编号、图像、图表标题、表格、表格标题、印章、图表标题、图表、页眉图像、页脚图像、侧栏文本",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-L_infer.tar",
    ),
    "pp_doclayout_m": ModelInfo(
        name="PP-DocLayout-M",
        display_name="PP-DocLayout M版面分析模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=22.6,
        description="中等精度版面分析，平衡速度与精度",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-M_infer.tar",
    ),
    "pp_doclayout_s": ModelInfo(
        name="PP-DocLayout-S",
        display_name="PP-DocLayout S版面分析模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=4.8,
        description="轻量版面分析，快速处理",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-S_infer.tar",
    ),
}

# 文档子区域检测模型 - 用于检测多栏文档的每个子文章区域
LAYOUT_BLOCK_MODELS = {
    "pp_docblocklayout": ModelInfo(
        name="PP-DocBlockLayout",
        display_name="文档子区域检测模型",
        category=ModelCategory.LAYOUT_BLOCK,
        size_mb=123.9,
        description="文档子区域检测，能检测多栏报纸、杂志的每个子文章文本区域",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocBlockLayout_infer.tar",
    ),
}

# 表格区域检测模型
LAYOUT_TABLE_MODELS = {
    "picodet_layout_1x_table": ModelInfo(
        name="PicoDet_layout_1x_table",
        display_name="表格区域检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=7.4,
        description="专门用于检测文档中的表格区域，中英文表格通用",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_table_infer.tar",
    ),
}

# 英文版面检测模型 - 5类区域
LAYOUT_EN_MODELS = {
    "picodet_layout_1x": ModelInfo(
        name="PicoDet_layout_1x",
        display_name="英文版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=7.4,
        description="英文文档版面检测，识别文字、标题、表格、图片、列表5类区域",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_infer.tar",
    ),
}

# 3类版面检测模型 - 表格、图像、印章
LAYOUT_3CLS_MODELS = {
    "picodet_s_layout_3cls": ModelInfo(
        name="PicoDet-S_layout_3cls",
        display_name="轻量3类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=4.8,
        description="轻量3类版面检测，识别表格、图像、印章",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_3cls_infer.tar",
    ),
    "picodet_l_layout_3cls": ModelInfo(
        name="PicoDet-L_layout_3cls",
        display_name="标准3类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=22.6,
        description="标准3类版面检测，识别表格、图像、印章",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-L_layout_3cls_infer.tar",
    ),
    "rt_detr_h_layout_3cls": ModelInfo(
        name="RT-DETR-H_layout_3cls",
        display_name="高精度3类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=470.1,
        description="高精度3类版面检测，识别表格、图像、印章，mAP达95.8%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-H_layout_3cls_infer.tar",
    ),
}

# 17类版面检测模型 - 段落标题、图片、文本、数字、摘要等
LAYOUT_17CLS_MODELS = {
    "picodet_s_layout_17cls": ModelInfo(
        name="PicoDet-S_layout_17cls",
        display_name="轻量17类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=4.8,
        description="轻量17类版面检测，识别段落标题、图片、文本、数字、摘要、内容、图表标题、公式、表格、表格标题、参考文献、文档标题、脚注、页眉、算法、页脚、印章",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_17cls_infer.tar",
    ),
    "picodet_l_layout_17cls": ModelInfo(
        name="PicoDet-L_layout_17cls",
        display_name="标准17类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=22.6,
        description="标准17类版面检测",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-L_layout_17cls_infer.tar",
    ),
    "rt_detr_h_layout_17cls": ModelInfo(
        name="RT-DETR-H_layout_17cls",
        display_name="高精度17类版面检测模型",
        category=ModelCategory.LAYOUT_DETECTION,
        size_mb=470.2,
        description="高精度17类版面检测，mAP达98.3%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-H_layout_17cls_infer.tar",
    ),
}

# ============================================================================
# 表格识别模型
# ============================================================================

TABLE_STRUCTURE_MODELS = {
    "slanet": ModelInfo(
        name="SLANet",
        display_name="表格结构识别模型",
        category=ModelCategory.TABLE_STRUCTURE,
        size_mb=6.9,
        description="表格结构识别，预测表格单元格坐标和结构",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANet_infer.tar",
    ),
    "slanet_plus": ModelInfo(
        name="SLANet_plus",
        display_name="表格结构识别增强模型",
        category=ModelCategory.TABLE_STRUCTURE,
        size_mb=6.9,
        description="增强版表格结构识别，提升复杂表格处理能力",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANet_plus_infer.tar",
    ),
    "slanext_wired": ModelInfo(
        name="SLANeXt_wired",
        display_name="有线表格结构识别模型",
        category=ModelCategory.TABLE_STRUCTURE,
        size_mb=351.0,
        description="高精度有线表格结构识别，基于SLANeXt架构",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wired_infer.tar",
    ),
    "slanext_wireless": ModelInfo(
        name="SLANeXt_wireless",
        display_name="无线表格结构识别模型",
        category=ModelCategory.TABLE_STRUCTURE,
        size_mb=351.0,
        description="高精度无线表格结构识别，基于SLANeXt架构",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wireless_infer.tar",
    ),
}

TABLE_CELLS_MODELS = {
    "rt_detr_l_wired_table_cell": ModelInfo(
        name="RT-DETR-L_wired_table_cell_det",
        display_name="有线表格单元格检测模型",
        category=ModelCategory.TABLE_CELLS,
        size_mb=124.0,
        description="高精度有线表格单元格检测",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wired_table_cell_det_infer.tar",
    ),
    "rt_detr_l_wireless_table_cell": ModelInfo(
        name="RT-DETR-L_wireless_table_cell_det",
        display_name="无线表格单元格检测模型",
        category=ModelCategory.TABLE_CELLS,
        size_mb=124.0,
        description="高精度无线表格单元格检测",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wireless_table_cell_det_infer.tar",
    ),
}

TABLE_CLASSIFICATION_MODELS = {
    "pp_lcnet_table_cls": ModelInfo(
        name="PP-LCNet_x1_0_table_cls",
        display_name="表格分类模型",
        category=ModelCategory.TABLE_CLASSIFICATION,
        size_mb=6.6,
        description="表格类型分类，识别有线表格/无线表格",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_table_cls_infer.tar",
    ),
}

# ============================================================================
# 公式识别模型
# ============================================================================

FORMULA_RECOGNITION_MODELS = {
    "latex_ocr": ModelInfo(
        name="LaTeX_OCR_rec",
        display_name="LaTeX-OCR公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=99.0,
        description="基于LaTeX-OCR的公式识别模型",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/LaTeX_OCR_rec_infer.tar",
    ),
    "pp_formulanet_s": ModelInfo(
        name="PP-FormulaNet-S",
        display_name="PP-FormulaNet S公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=224.0,
        description="轻量公式识别模型，支持中英文LaTeX公式识别",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-S_infer.tar",
    ),
    "pp_formulanet_plus_s": ModelInfo(
        name="PP-FormulaNet_plus-S",
        display_name="PP-FormulaNet+ S公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=248.0,
        description="增强版轻量公式识别，中文BLEU达53.32%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-S_infer.tar",
    ),
    "pp_formulanet_plus_m": ModelInfo(
        name="PP-FormulaNet_plus-M",
        display_name="PP-FormulaNet+ M公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=592.0,
        description="中量公式识别模型，中文BLEU达89.76%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-M_infer.tar",
    ),
    "pp_formulanet_plus_l": ModelInfo(
        name="PP-FormulaNet_plus-L",
        display_name="PP-FormulaNet+ L公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=698.0,
        description="高精度公式识别模型，支持复杂数学公式，中文BLEU达90.64%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-L_infer.tar",
    ),
    "pp_formulanet_l": ModelInfo(
        name="PP-FormulaNet-L",
        display_name="PP-FormulaNet L公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=695.0,
        description="高精度公式识别模型",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-L_infer.tar",
    ),
    "unimernet": ModelInfo(
        name="UniMERNet",
        display_name="UniMERNet公式识别模型",
        category=ModelCategory.FORMULA_RECOGNITION,
        size_mb=1530.0,
        description="超大规模通用公式识别模型，支持复杂数学公式，英文BLEU达85.91%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UniMERNet_infer.tar",
    ),
}

# ============================================================================
# 文档视觉语言模型 (Doc VLM)
# ============================================================================

# ============================================================================
# PaddleOCR-VL 文档解析模型 (2025年10月新发布，SOTA)
# 这是与PP-DocBee不同的模型，专为文档解析设计
# ============================================================================

OCR_VL_MODELS = {
    "paddleocr_vl_0_9b": ModelInfo(
        name="PaddleOCR-VL-0.9B",
        display_name="PaddleOCR-VL 0.9B 文档解析模型",
        category=ModelCategory.OCR_VL,
        size_mb=1800.0,
        description="超紧凑0.9B参数VLM，SOTA文档解析，支持109种语言，擅长文本/表格/公式/图表识别",
        download_url="https://huggingface.co/PaddlePaddle/PaddleOCR-VL/resolve/main/paddleocr_vl_0.9b_infer.tar",
        language="multilingual",
    ),
}

# ============================================================================
# PP-DocBee 文档理解模型 (用于文档问答，与PaddleOCR-VL不同)
# ============================================================================

DOC_VLM_MODELS = {
    "pp_docbee2_3b": ModelInfo(
        name="PP-DocBee2-3B",
        display_name="PP-DocBee2-3B 文档理解模型",
        category=ModelCategory.DOC_VLM,
        size_mb=7600.0,
        description="3B参数文档理解模型，支持文档问答，精度提升11.4%",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocBee2-3B_infer.tar",
    ),
    "pp_docbee_2b": ModelInfo(
        name="PP-DocBee-2B",
        display_name="PP-DocBee-2B 文档理解模型",
        category=ModelCategory.DOC_VLM,
        size_mb=4200.0,
        description="2B参数文档理解模型，支持文档问答、内容提取",
        download_url="https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocBee-2B_infer.tar",
    ),
}

# ============================================================================
# 合并所有模型
# ============================================================================

ALL_MODELS = {
    **TEXT_DETECTION_MODELS,
    **TEXT_RECOGNITION_MODELS,
    **MULTILANGUAGE_RECOGNITION_MODELS,  # 多语言V5可选下载
    **ORIENTATION_MODELS,
    **DOC_UNWARPING_MODELS,
    **LAYOUT_DETECTION_MODELS,
    **LAYOUT_BLOCK_MODELS,
    **LAYOUT_TABLE_MODELS,
    **LAYOUT_EN_MODELS,
    **LAYOUT_3CLS_MODELS,
    **LAYOUT_17CLS_MODELS,
    **TABLE_STRUCTURE_MODELS,
    **TABLE_CELLS_MODELS,
    **TABLE_CLASSIFICATION_MODELS,
    **FORMULA_RECOGNITION_MODELS,
    **OCR_VL_MODELS,  # PaddleOCR-VL文档解析
    **DOC_VLM_MODELS,  # PP-DocBee文档问答
}

# ============================================================================
# 模型预设组合 - 功能渐进式设计
# ============================================================================

MODEL_PRESETS = {
    # 层级1: 核心OCR - 最简配置
    "core_ocr": ModelPreset(
        id="core_ocr",
        name="核心OCR",
        description="包含文本检测和识别功能，适用于简单的文档OCR场景",
        models=["ppocrv5_server_det", "ppocrv5_server_rec"],
        total_size_mb=182.0,
        recommended_for="日常文档截图、屏幕文本识别等基础场景",
    ),
    # 层级2: 标准OCR - 核心 + 图像预处理
    "standard_ocr": ModelPreset(
        id="standard_ocr",
        name="标准OCR",
        description="核心OCR + 文档方向分类 + 文档图像矫正，处理旋转和弯曲文档",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
        ],
        total_size_mb=219.3,
        recommended_for="扫描文档、照片、书籍、曲面文档等场景",
    ),
    # 层级3: 表格OCR - 标准 + 表格识别
    "table_ocr": ModelPreset(
        id="table_ocr",
        name="表格识别",
        description="标准OCR + 表格区域检测 + 表格结构识别 + 表格分类",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
            "picodet_layout_1x_table",
            "slanet_plus",
            "pp_lcnet_table_cls",
        ],
        total_size_mb=235.3,
        recommended_for="财务报表、表格文档、简历等含表格场景",
    ),
    # 层级4: 版面OCR - 表格OCR + 版面分析
    "layout_ocr": ModelPreset(
        id="layout_ocr",
        name="版面分析",
        description="表格OCR + 通用版面分析 + 子区域检测",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
            "picodet_layout_1x_table",
            "slanet_plus",
            "pp_lcnet_table_cls",
            "pp_doclayout_plus_l",  # 高精度版面
            "pp_docblocklayout",  # 子区域检测
        ],
        total_size_mb=486.2,  # 235.3 + 126 + 124
        recommended_for="论文、杂志、报纸等多区域复杂文档",
    ),
    # 层级5: 公式OCR - 版面OCR + 公式识别
    "formula_ocr": ModelPreset(
        id="formula_ocr",
        name="公式识别",
        description="版面OCR + 公式识别，支持中英文LaTeX公式",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
            "picodet_layout_1x_table",
            "slanet_plus",
            "pp_lcnet_table_cls",
            "pp_doclayout_plus_l",
            "pp_docblocklayout",
            "pp_formulanet_plus_m",  # 中量高精度公式
        ],
        total_size_mb=1078.2,  # 486.2 + 592
        recommended_for="学术论文、教材、试卷等含公式的文档",
    ),
    # 层级6: 文档解析 - PaddleOCR-VL SOTA模型
    "ocr_vl": ModelPreset(
        id="ocr_vl",
        name="文档解析",
        description="PaddleOCR-VL 0.9B SOTA模型，端到端文档解析，支持文本/表格/公式/图表",
        models=[
            "paddleocr_vl_0_9b",  # 0.9B参数，SOTA文档解析
        ],
        total_size_mb=1800.0,
        recommended_for="端到端文档解析、复杂文档处理、多语言109种语言支持",
    ),
    # 层级7: 智能文档 - 公式OCR + Doc VLM
    "smart_doc": ModelPreset(
        id="smart_doc",
        name="智能问答",
        description="公式OCR + PP-DocBee文档问答模型，支持文档理解、问答、内容提取",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
            "picodet_layout_1x_table",
            "slanet_plus",
            "pp_lcnet_table_cls",
            "pp_doclayout_plus_l",
            "pp_docblocklayout",
            "pp_formulanet_plus_m",
            "pp_docbee2_3b",  # 3B参数Doc VLM
        ],
        total_size_mb=8678.2,  # 1078.2 + 7600
        recommended_for="需要文档理解、多模态问答、内容提取的智能文档场景",
    ),
    # 层级8: 全功能 - 智能文档 + 高精度表格模型
    "full_ocr": ModelPreset(
        id="full_ocr",
        name="全功能",
        description="智能文档 + 高精度表格结构模型 + 高精度单元格检测",
        models=[
            "ppocrv5_server_det",
            "ppocrv5_server_rec",
            "pp_lcnet_doc_ori",
            "uvdoc",
            "picodet_layout_1x_table",
            "slanet_plus",
            "pp_lcnet_table_cls",
            "pp_doclayout_plus_l",
            "pp_docblocklayout",
            "pp_formulanet_plus_m",
            "pp_docbee2_3b",
            # 高精度表格模型
            "slanext_wired",
            "slanext_wireless",
            "rt_detr_l_wired_table_cell",
            "rt_detr_l_wireless_table_cell",
        ],
        total_size_mb=10304.2,  # 8678.2 + 351 + 351 + 124 + 124 + 702 - 重复计算
        recommended_for="需要处理各类复杂文档的专业场景，高精度表格处理",
    ),
}

# ============================================================================
# 辅助函数
# ============================================================================


def get_model_by_id(model_id: str) -> Optional[ModelInfo]:
    """根据模型ID获取模型信息"""
    return ALL_MODELS.get(model_id)


def get_preset_by_id(preset_id: str) -> Optional[ModelPreset]:
    """根据预设ID获取预设信息"""
    return MODEL_PRESETS.get(preset_id)


def get_models_by_category(category: ModelCategory) -> List[ModelInfo]:
    """获取指定类别的所有模型"""
    return [m for m in ALL_MODELS.values() if m.category == category]


def get_all_presets() -> List[ModelPreset]:
    """获取所有预设组合"""
    return list(MODEL_PRESETS.values())


def calculate_preset_size(preset_id: str) -> float:
    """计算预设组合的总大小"""
    preset = get_preset_by_id(preset_id)
    if not preset:
        return 0.0

    total = 0.0
    seen = set()
    for model_id in preset.models:
        if model_id not in seen:
            model = get_model_by_id(model_id)
            if model:
                total += model.size_mb
                seen.add(model_id)
    return round(total, 1)


def get_recommended_presets_for_scenario(scenario: str) -> List[ModelPreset]:
    """根据使用场景获取推荐的预设组合

    Args:
        scenario: 使用场景描述
    """
    scenario_map = {
        "simple": ["core_ocr"],
        "document": ["standard_ocr"],
        "table": ["table_ocr"],
        "layout": ["layout_ocr"],
        "formula": ["formula_ocr"],
        "smart": ["smart_doc"],
        "complex": ["full_ocr"],
    }

    preset_ids = scenario_map.get(scenario, [])
    return [get_preset_by_id(pid) for pid in preset_ids if get_preset_by_id(pid)]


def get_all_models_grouped() -> Dict[str, List[ModelInfo]]:
    """获取按类别分组的模型列表"""
    groups = {}
    for model in ALL_MODELS.values():
        category = model.category.value
        if category not in groups:
            groups[category] = []
        groups[category].append(model)
    return groups


# 导出模型选择配置类
class ModelDownloadConfig:
    """模型下载配置类，提供便捷的模型选择接口"""

    # 推荐的模型组合（按功能渐进）
    RECOMMENDED_COMBINATIONS = {
        "core": {
            "models": ["ppocrv5_server_det", "ppocrv5_server_rec"],
            "total_size_mb": 182.0,
            "description": "核心OCR，仅文本检测和识别",
        },
        "standard": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
            ],
            "total_size_mb": 219.3,
            "description": "标准OCR，包含文档预处理",
        },
        "table": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
                "picodet_layout_1x_table",
                "slanet_plus",
                "pp_lcnet_table_cls",
            ],
            "total_size_mb": 235.3,
            "description": "表格识别OCR",
        },
        "layout": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
                "picodet_layout_1x_table",
                "slanet_plus",
                "pp_lcnet_table_cls",
                "pp_doclayout_plus_l",
                "pp_docblocklayout",
            ],
            "total_size_mb": 486.2,
            "description": "版面分析OCR",
        },
        "formula": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
                "picodet_layout_1x_table",
                "slanet_plus",
                "pp_lcnet_table_cls",
                "pp_doclayout_plus_l",
                "pp_docblocklayout",
                "pp_formulanet_plus_m",
            ],
            "total_size_mb": 1078.2,
            "description": "公式识别OCR",
        },
        "ocr_vl": {
            "models": ["paddleocr_vl_0_9b"],
            "total_size_mb": 1800.0,
            "description": "PaddleOCR-VL 0.9B SOTA文档解析，端到端多模态",
        },
        "smart": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
                "picodet_layout_1x_table",
                "slanet_plus",
                "pp_lcnet_table_cls",
                "pp_doclayout_plus_l",
                "pp_docblocklayout",
                "pp_formulanet_plus_m",
                "pp_docbee2_3b",
            ],
            "total_size_mb": 8678.2,
            "description": "智能问答，包含PP-DocBee文档问答",
        },
        "full": {
            "models": [
                "ppocrv5_server_det",
                "ppocrv5_server_rec",
                "pp_lcnet_doc_ori",
                "uvdoc",
                "picodet_layout_1x_table",
                "slanet_plus",
                "pp_lcnet_table_cls",
                "pp_doclayout_plus_l",
                "pp_docblocklayout",
                "pp_formulanet_plus_m",
                "pp_docbee2_3b",
                "slanext_wired",
                "slanext_wireless",
                "rt_detr_l_wired_table_cell",
                "rt_detr_l_wireless_table_cell",
            ],
            "total_size_mb": 10304.2,
            "description": "全功能OCR，包含所有模块",
        },
    }

    @classmethod
    def get_combination(cls, name: str) -> Optional[Dict]:
        """获取指定名称的模型组合"""
        return cls.RECOMMENDED_COMBINATIONS.get(name)

    @classmethod
    def get_all_combinations(cls) -> Dict[str, Dict]:
        """获取所有推荐的模型组合"""
        return cls.RECOMMENDED_COMBINATIONS
