/**
 * Track Model — Chuẩn hóa dữ liệu bài hát.
 *
 * Đóng gói metadata + thông tin người yêu cầu để sử dụng xuyên suốt:
 * Queue, Now Playing, History, Requester display, Permission check.
 */

class Track {
    /**
     * @param {object} kazagumoTrack - Track object từ Kazagumo search result
     * @param {import('discord.js').User} requester - Discord user đã yêu cầu bài hát
     */
    constructor(kazagumoTrack, requester) {
        /** Tiêu đề bài hát */
        this.title = kazagumoTrack.title || 'Unknown Title';

        /** Nghệ sĩ / Tác giả */
        this.author = kazagumoTrack.author || 'Unknown Artist';

        /** URL gốc (YouTube, Spotify, SoundCloud...) */
        this.uri = kazagumoTrack.uri || '';

        /** Thời lượng bài hát tính bằng mili-giây */
        this.duration = kazagumoTrack.length || 0;

        /** Bài hát có phải livestream không */
        this.isStream = kazagumoTrack.isStream || false;

        /** URL ảnh thumbnail */
        this.thumbnail = kazagumoTrack.thumbnail || null;

        /** Nguồn phát (youtube, spotify, soundcloud...) */
        this.source = kazagumoTrack.sourceName || 'unknown';

        /** ID định danh nguồn (videoId, trackId...) */
        this.identifier = kazagumoTrack.identifier || '';

        /** Dữ liệu track gốc từ Kazagumo (cần cho player.play()) */
        this.raw = kazagumoTrack;

        // --- Requester Metadata ---

        /** ID Discord của người yêu cầu */
        this.requesterId = requester ? requester.id : null;

        /** Tên hiển thị của người yêu cầu */
        this.requesterName = requester ? (requester.globalName || requester.username) : 'Unknown';

        /** Avatar URL của người yêu cầu */
        this.requesterAvatar = requester ? requester.displayAvatarURL({ size: 64 }) : null;

        /** Thời điểm bài hát được thêm vào queue */
        this.addedAt = Date.now();
    }

    /**
     * Tạo Track từ Kazagumo track object (đã có requester gắn sẵn).
     * Kazagumo gắn requester vào track khi search, nên ta đọc trực tiếp.
     * @param {object} kazagumoTrack
     * @returns {Track}
     */
    static fromKazagumo(kazagumoTrack) {
        return new Track(kazagumoTrack, kazagumoTrack.requester || null);
    }
}

module.exports = Track;
