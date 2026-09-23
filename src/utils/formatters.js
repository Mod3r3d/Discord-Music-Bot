/**
 * Utility functions — Định dạng thời gian và thanh tiến trình.
 */

/**
 * Chuyển mili-giây sang chuỗi thời gian đọc được.
 * @param {number} ms - Thời gian tính bằng mili-giây
 * @returns {string} Chuỗi dạng "mm:ss" hoặc "hh:mm:ss"
 *
 * @example
 * formatDuration(215000)  // "03:35"
 * formatDuration(3723000) // "01:02:03"
 */
function formatDuration(ms) {
    if (!ms || ms <= 0) return '00:00';

    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const pad = (n) => String(n).padStart(2, '0');

    if (hours > 0) {
        return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }
    return `${pad(minutes)}:${pad(seconds)}`;
}

/**
 * Tạo thanh tiến trình dạng ký tự.
 * @param {number} currentMs - Vị trí phát hiện tại (mili-giây)
 * @param {number} totalMs - Tổng thời lượng (mili-giây)
 * @param {number} [length=15] - Số ký tự của thanh tiến trình
 * @returns {string} Thanh tiến trình, VD: "▶ ████████░░░░░░░ 02:15 / 04:30"
 */
function createProgressBar(currentMs, totalMs, length = 15) {
    if (!totalMs || totalMs <= 0) {
        return `🔴 LIVE — ${formatDuration(currentMs)}`;
    }

    const progress = Math.min(currentMs / totalMs, 1);
    const filledLength = Math.round(progress * length);
    const emptyLength = length - filledLength;

    const filled = '█'.repeat(filledLength);
    const empty = '░'.repeat(emptyLength);

    return `▶ ${filled}${empty} ${formatDuration(currentMs)} / ${formatDuration(totalMs)}`;
}

/**
 * Rút gọn chuỗi nếu quá dài.
 * @param {string} str - Chuỗi gốc
 * @param {number} [maxLength=50] - Độ dài tối đa
 * @returns {string} Chuỗi đã rút gọn
 */
function truncate(str, maxLength = 50) {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength - 3) + '...';
}

/**
 * Tính tổng thời lượng của một mảng tracks (mili-giây).
 * @param {Array} tracks - Mảng các track object có thuộc tính duration hoặc length
 * @returns {number} Tổng thời lượng (ms)
 */
function totalDuration(tracks) {
    if (!tracks || !tracks.length) return 0;
    return tracks.reduce((sum, t) => {
        const dur = t.duration || t.length || 0;
        return sum + dur;
    }, 0);
}

module.exports = {
    formatDuration,
    createProgressBar,
    truncate,
    totalDuration
};
