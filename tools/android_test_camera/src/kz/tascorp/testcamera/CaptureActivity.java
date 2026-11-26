package kz.tascorp.testcamera;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.media.ExifInterface;
import android.os.Build;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Тестовая камера для автотестов на эмуляторе. У эмулятора камера снимает свою виртуальную
 * сцену — приложение такие снимки иногда не принимает, и подставить своё фото нельзя.
 *
 * Отвечает на android.media.action.IMAGE_CAPTURE (системную камеру тесты на время сессии
 * отключают) и сразу, без экрана, возвращает снимок в EXTRA_OUTPUT:
 *   1. файл next.jpg из своей папки (/sdcard/Android/data/kz.tascorp.testcamera/files/),
 *      если тест его туда положил, — только на этот снимок, после чего файл удаляется;
 *   2. иначе — картинку с подписью «TasCorp autotest», номером снимка и временем.
 *
 * В файл пишутся EXIF, как у настоящей камеры: дата съёмки, производитель/модель, ориентация,
 * размеры и координаты. Без них сервер принимал фото авто и техпаспорта, но оценщик их не
 * видел (фото документа заёмщика — видел).
 */
public class CaptureActivity extends Activity {
    private static final String TAG = "TasTestCamera";
    private static final int[] COLORS = {
        0xFF1E88E5, 0xFF00897B, 0xFF3949AB, 0xFF43A047, 0xFFFB8C00, 0xFF8E24AA,
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        int shot = nextShotNumber();
        Bitmap image = null;
        File next = new File(getExternalFilesDir(null), "next.jpg");
        if (next.exists()) {
            image = BitmapFactory.decodeFile(next.getAbsolutePath());
            next.delete();
            Log.i(TAG, "shot #" + shot + " from " + next);
        }
        if (image == null) {
            image = generated(shot);
            Log.i(TAG, "shot #" + shot + " generated");
        }
        Intent request = getIntent();
        Uri output = request.getParcelableExtra(MediaStore.EXTRA_OUTPUT);
        Intent result = new Intent();
        try {
            if (output != null) {
                File jpeg = new File(getCacheDir(), "shot.jpg");
                try (OutputStream out = new FileOutputStream(jpeg)) {
                    image.compress(Bitmap.CompressFormat.JPEG, 90, out);
                }
                writeExif(jpeg, image.getWidth(), image.getHeight());
                try (OutputStream out = getContentResolver().openOutputStream(output);
                     InputStream in = new FileInputStream(jpeg)) {
                    byte[] buf = new byte[64 * 1024];
                    for (int n; (n = in.read(buf)) > 0; ) out.write(buf, 0, n);
                }
                jpeg.delete();
            } else {
                result.putExtra("data", Bitmap.createScaledBitmap(image, 400, 300, true));
            }
            setResult(RESULT_OK, result);
        } catch (Exception e) {
            Log.e(TAG, "cannot write photo", e);
            setResult(RESULT_CANCELED);
        }
        finish();
    }

    /** EXIF как у камеры телефона. Координаты — центр Алматы (у эмулятора своих нет). */
    private static void writeExif(File jpeg, int width, int height) throws IOException {
        ExifInterface exif = new ExifInterface(jpeg.getAbsolutePath());
        Date now = new Date();
        String stamp = new SimpleDateFormat("yyyy:MM:dd HH:mm:ss", Locale.US).format(now);
        exif.setAttribute(ExifInterface.TAG_MAKE, Build.MANUFACTURER);
        exif.setAttribute(ExifInterface.TAG_MODEL, Build.MODEL);
        exif.setAttribute(ExifInterface.TAG_SOFTWARE, "TasCorp Test Camera");
        exif.setAttribute(ExifInterface.TAG_DATETIME, stamp);
        exif.setAttribute(ExifInterface.TAG_DATETIME_ORIGINAL, stamp);
        exif.setAttribute(ExifInterface.TAG_DATETIME_DIGITIZED, stamp);
        exif.setAttribute(ExifInterface.TAG_ORIENTATION, String.valueOf(ExifInterface.ORIENTATION_NORMAL));
        exif.setAttribute(ExifInterface.TAG_IMAGE_WIDTH, String.valueOf(width));
        exif.setAttribute(ExifInterface.TAG_IMAGE_LENGTH, String.valueOf(height));
        exif.setAttribute(ExifInterface.TAG_PIXEL_X_DIMENSION, String.valueOf(width));
        exif.setAttribute(ExifInterface.TAG_PIXEL_Y_DIMENSION, String.valueOf(height));
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE, dms(43.238949));
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE_REF, "N");
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE, dms(76.889709));
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE_REF, "E");
        SimpleDateFormat utc = new SimpleDateFormat("yyyy:MM:dd HH:mm:ss", Locale.US);
        utc.setTimeZone(TimeZone.getTimeZone("UTC"));
        String[] gps = utc.format(now).split(" ");
        exif.setAttribute(ExifInterface.TAG_GPS_DATESTAMP, gps[0]);
        exif.setAttribute(ExifInterface.TAG_GPS_TIMESTAMP, gps[1]);
        exif.saveAttributes();
    }

    /** Градусы → EXIF-формат «град/1,мин/1,сек*1000/1000». */
    private static String dms(double degrees) {
        int d = (int) degrees;
        double m = (degrees - d) * 60;
        int min = (int) m;
        int sec = (int) Math.round((m - min) * 60 * 1000);
        return d + "/1," + min + "/1," + sec + "/1000";
    }

    private int nextShotNumber() {
        SharedPreferences prefs = getSharedPreferences("camera", MODE_PRIVATE);
        int shot = prefs.getInt("shot", 0) + 1;
        prefs.edit().putInt("shot", shot).apply();
        return shot;
    }

    private static Bitmap generated(int shot) {
        Bitmap bmp = Bitmap.createBitmap(1600, 1200, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        canvas.drawColor(COLORS[(shot - 1) % COLORS.length]);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(Color.WHITE);
        paint.setTextSize(90);
        paint.setFakeBoldText(true);
        paint.setTextAlign(Paint.Align.CENTER);
        String time = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date());
        String[] lines = {"TasCorp autotest", "снимок №" + shot, time};
        for (int i = 0; i < lines.length; i++) {
            canvas.drawText(lines[i], 800, 480 + i * 130, paint);
        }
        return bmp;
    }
}
