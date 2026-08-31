#pragma once
#define ET_DLL_EXPORTS

#ifdef ET_DLL_EXPORTS
#define ET_DLL_API __declspec(dllexport)
#else
#define ET_DLL_API __declspec(dllimport)
#endif

/**
 * @brief 返回状态码定义
 */
enum ET_ReturnCode
{
    ET_SUCCESS = 0,         ///< 成功，当前操作执行完成
    ET_CALI_CONTINUE = 1,   ///< 标定过程中，继续使用当前标定点进行采集
    ET_CALI_NEXT_POINT = 2, ///< 标定过程中，需要切换到下一个标定点
    ET_FAILED = 9,          ///< 失败
};

extern "C"
{
/**
 * @brief 获取版本号
 * @return 返回版本字符串
 */
ET_DLL_API const char* deep_gaze_get_version();

/**
 * @brief 设置日志
 * @param valid 是否开启日志（0:关闭，1:开启）
 * @param log_Path 日志保存路径
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_log(int valid, char* log_Path);

/**
 * @brief 查询当前生效的相机帧率模式及 ROI 几何（运行时确定，源自
 *        dp_camera_tunning.bin 的 "camera_mode" 字段）。
 *
 * 客户端（如 DllTest）不应再编译期硬编码 ROI 尺寸/偏置——库才是唯一真值源。
 * 请在 deep_gaze_init() 成功之后调用本接口，据此分配预览缓冲与贴图矩形。
 *
 * @param mode      输出：模式枚举值（见 CameraMode.h 中 CameraMode）；可传 nullptr
 * @param left_roi  输出：左相机 ROI，长度4 = {x, y, w, h}，传感器全图(1280x1024)坐标系；
 *                  既是 ROI 缓冲尺寸(w*h)，也是贴回画布的位置(x,y)。可传 nullptr
 * @param right_roi 输出：右相机 ROI，长度4 = {x, y, w, h}，定义同 left_roi。可传 nullptr
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_get_camera_mode(
        int* mode,
        int* left_roi,
        int* right_roi);

/**
 * @brief 设置相机帧率模式（仅设置 mode，ROI/曝光仍为内置）。
 *
 * 仅适用于 dp_camera_tunning.bin 中带 "sync_400" 字样的设备：此类设备同时支持
 * 原生 SYNC_400 与降频 SYNC_200。设 *mode = CAMERA_MODE_SYNC_200(3) 时以 sync_200
 * 运行（ROI 1024×1024、曝光 2500?s，与 200 设备一致），随后 deep_gaze_get_camera_mode
 * 也返回 200 的信息；设 *mode = CAMERA_MODE_SYNC_400(0) 则维持原生 400。
 *
 * 约定：必须在 deep_gaze_init() 之前调用——init 读取 bin 时确认设备能力并一次性套用，
 * 相机据此打开（不在运行中重配置已打开的相机）。
 *
 * @param mode 输入：目标模式枚举（仅接受 CAMERA_MODE_SYNC_400=0 / CAMERA_MODE_SYNC_200=3）
 * @return ET_SUCCESS：请求被接受；ET_FAILED：mode 为空/非法，或本设备非 sync_400 设备
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_camera_mode(int* mode);

/**
 * @brief 设置眼睛模式
 * @param mode 模式选择
 *              - 0: 双眼模式（默认模式）
 *              - -1: 仅左眼模式
 *              - 1: 仅右眼模式
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_eye_mode(int mode);

/**
 * @brief 设置相机参数
 * @param camera_param 相机参数数组
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_camera_param(float* camera_param);

/**
 * @brief 设置Kappa滤波开关
 *
 * 默认开启（值为1），如果没有标定或者不需要补偿，可以设置为0关闭
 *
 * @param kappa_filter Kappa滤波状态（0:关闭，1:开启）
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_kappa_filter(int kappa_filter);

/**
 * @brief 设置前瞻时间
 * @param look_ahead 前瞻时间
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_look_ahead(int look_ahead);

/**
 * @brief 初始化
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_init();

/**
 * @brief 重新进入标定流程
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_recalibrate();

/**
 * @brief 获取用户眼睛三维位置
 *
 * @param eyepos 输出参数，长度为3，对应 (x, y, z)，单位：mm
 *
 * 坐标说明：
 *   - 屏幕中心 = (172.08, 96.795)
 *   - 屏幕尺寸 ≈ [344.16, 193.59] = [172.08*2, 96.795*2]
 *
 * 推荐范围：
 *   - x ∈ [172.08 - 32 - 30, 172.08 - 32 + 30]
 *   - y ∈ [96.795 - 40 - 30, 96.795 - 40 + 30]
 *   - z ∈ [-580 - 50, -580 + 50]
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_face_pos(float* eyepos);

/**
 * @brief 获取预处理后的人脸灰度图
 *
 * @param image_data 输出图像数据指针
 * @param width 输出图像宽度
 * @param height 输出图像高度
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_face_image(char** image_data, int* width, int* height);

/**
 * @brief 设置标定模式
 *
 * @param mode 标定模式
 *              - 2: 2点标定模式
 *              - 4: 4点标定模式
 *              - 5: 5点标定模式
 *              - 其他: 当前版本暂不支持
 * @param cali_points 标定点坐标数组，长度固定为 2 * mode
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_cali_mode(int mode, float* cali_points);

/**
 * @brief 执行标定
 *
 * @param cali_point_id 当前标定点ID
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_cali(const int cali_point_id);

/**
 * @brief 获取注视点信息
 *
 * @param pt 输出数组，长度固定为11：
 *        - pt[0]: 左眼注视点 x (范围 0~1920)
 *        - pt[1]: 左眼注视点 y (范围 0~1080)
 *        - pt[2]: 左眼瞳孔直径 (范围 0~10 mm)
 *
 *        - pt[3]: 右眼注视点 x (范围 0~1920)
 *        - pt[4]: 右眼注视点 y (范围 0~1080)
 *        - pt[5]: 右眼瞳孔直径 (范围 0~10 mm)
 *
 *        - pt[6]: 单眼平均注视点 x
 *        - pt[7]: 单眼平均注视点 y
 *
 *        - pt[8]: 状态标志：
 *                 0: 正常
 *                 1: 丢失左眼
 *                 2: 丢失右眼
 *                 3: 双眼均丢失
 *
 *        - pt[9]: 双眼融合注视点 x (范围 0~1920)
 *        - pt[10]: 双眼融合注视点 y (范围 0~1080)
 *
 * @param timeStamp 时间戳（格式：时:分:秒:毫秒）
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_est(float* pt, long long* timeStamp);

/**
 * @brief 获取预览信息（调试接口）
 *
 * 图像与 eye_rects/pupil_centers/glint_centers 坐标系自洽，可直接在返回图上绘制：
 *   - SYNC_200 模式：ROI 图已按 ROI 在整帧中的位置 padding 回整帧 1280x1024，
 *     eye_rects/pupil/glint 为整帧坐标，直接对得上图。
 *   - 其它模式：图维持各路 ROI 原始尺寸（不 padding），eye_rects/pupil/glint
 *     已减去 ROI 左上角并裁进 ROI 范围，直接画在 ROI 图上即可。
 *
 * @param img_1 左相机预览图像指针（SYNC_200 为 1280x1024，其它模式为左 ROI 尺寸）
 * @param img2  右相机预览图像指针（SYNC_200 为 1280x1024，其它模式为右 ROI 尺寸）
 *
 * @param eye_rects 眼睛区域数组，长度为16
 *                  表示4个 cv::Rect(x, y, w, h)
 *
 * @param pupil_centers 瞳孔中心数组，长度为8
 *                      表示4个点 (x, y)
 *
 * @param glint_centers 角膜反射点数组，长度为8
 *                      表示4个点 (x, y)
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_get_previewer(
        unsigned char** img_1,
        unsigned char** img2,
        float* eye_rects,
        float* pupil_centers,
        float* glint_centers);

/**
 * @brief 获取左右眼详细注视信息
 *
 * @param pt_l 左眼数据数组，长度14：
 *        [0] 注视点 x (0~1920)
 *        [1] 注视点 y (0~1080)
 *        [2] 瞳孔直径 (0~10 mm)
 *        [3~5] 瞳孔三维位置 (x,y,z)
 *        [6] 视线角 theta（弧度）
 *        [7] 视线角 phi（弧度）
 *        [8~10] 视线方向向量 (x,y,z)
 *        [11~12] 单眼注视点 (x,y)
 *        [13] 有效性标志（0:无效 1:有效）
 *
 * @param pt_r 右眼数据（定义同 pt_l）
 *
 * @param pt_bino 双眼融合数据，长度10：
 *        [0] 注视点 x (0~1920)
 *        [1] 注视点 y (0~1080)
 *        [2] 有效性标志（0:无效 1:有效）
 *        [3~9] 预留数据
 *
 * @param timestamp 时间戳
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_est_lr(
        float* pt_l,
        float* pt_r,
        float* pt_bino,
        long long* timestamp);

/**
 * @brief 获取完整注视信息（与帧率无关）
 *
 * 一次返回左/右/双眼全部结果。帧率模式由 dp_camera_tunning.bin 的
 * "camera_mode" 在运行时决定（见 deep_gaze_get_camera_mode），数据布局与帧率无关，
 * 故函数名不再带帧率后缀。
 *
 * @param pt 输出数组（长度38）：
 *        = pt_l(14) + pt_r(14) + pt_bino(10)
 *
 * @param timestamp 主时间戳
 *
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_est_full(
        float* pt,
        long long* timestamp);

/**
 * @brief 注视结果回调函数类型（基础类型 ABI，便于跨语言绑定）
 *
 * @param pt          长度38的注视结果数组（布局同 deep_gaze_est_full）
 * @param timestamp   该结果对应的相机曝光时间戳
 *                    - 同步模式（CAMERA_SYNC_MODE=1）: 左右相机时间戳一致
 *                    - 异步模式（CAMERA_SYNC_MODE=0）: 左/右相机时间戳交替
 * @param user_data   注册时传入的用户指针，库不解释其内容
 */
typedef void (*deep_gaze_est_callback)(
        const float* pt,
        long long timestamp,
        void* user_data);

/**
 * @brief 注册注视结果回调
 *
 * 回调由库内部以受控频率分发：
 *   - 同步模式: 400Hz
 *   - 异步模式: 800Hz（左右相机交替）
 *
 * 传入 cb=nullptr 取消回调（同时停止内部分发线程）。
 * 注册后会自动启动 FE → gaze 流水线，无需再单独调 deep_gaze_est_full。
 *
 * @param cb         结果回调；nullptr 表示取消
 * @param user_data  透传给回调的用户指针
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_set_est_callback(
        deep_gaze_est_callback cb,
        void* user_data);

/**
 * @brief 释放资源（程序退出时必须调用）
 * @return 返回状态码
 */
ET_ReturnCode ET_DLL_API deep_gaze_release();
}