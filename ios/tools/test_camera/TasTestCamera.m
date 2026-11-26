// Тестовая камера для iOS Simulator: у Simulator нет камеры, кнопка съёмки системного
// экрана неактивна, и фото в заявку не сделать.
//
// Подгружается в приложение только в автотестах (DYLD_INSERT_LIBRARIES, см. tests/conftest.py),
// бинарник приложения не меняется. Когда приложение открывает системную камеру
// (UIImagePickerController, sourceType = camera), поверх неё ставится свой слой —
// штатным API пикера (showsCameraControls = NO + cameraOverlayView): кнопка затвора
// «PhotoCapture» (тот же идентификатор, что у системной) и «Cancel». Затвор отдаёт приложению
// снимок через обычный делегат пикера — дальше приложение обрабатывает его как фото с камеры.
//
// Снимок (по приоритету):
//   1. Файл, путь к которому тест записал в TAS_TEST_CAMERA_NEXT — только на этот снимок
//      (файл-указатель после снимка удаляется). Так тест подставляет своё фото в конкретную ячейку.
//      Вместо пути можно записать «text:<строка>» — снимок с этой строкой крупным шрифтом
//      (чёрный на белом): так снимается «VIN код», бэкенд распознаёт VIN на фото (с 10.11.2026).
//   2. Следующий файл из TAS_TEST_CAMERA_DIR (jpg/png по кругу).
//   3. Сгенерированная картинка с подписью TAS_TEST_CAMERA_LABEL, временем и номером снимка.
#import <UIKit/UIKit.h>
#import <objc/runtime.h>

static NSUInteger gShot = 0;

static UIImage *TTCTextImage(NSString *text) {
    CGSize size = CGSizeMake(1600, 1200);
    UIGraphicsImageRendererFormat *fmt = [UIGraphicsImageRendererFormat defaultFormat];
    fmt.scale = 1;
    UIGraphicsImageRenderer *r = [[UIGraphicsImageRenderer alloc] initWithSize:size format:fmt];
    return [r imageWithActions:^(UIGraphicsImageRendererContext *ctx) {
        [UIColor.whiteColor setFill];
        UIRectFill(CGRectMake(0, 0, size.width, size.height));
        NSMutableParagraphStyle *p = [NSMutableParagraphStyle new];
        p.alignment = NSTextAlignmentCenter;
        [text drawInRect:CGRectMake(40, 500, size.width - 80, 200) withAttributes:@{
            NSFontAttributeName: [UIFont monospacedSystemFontOfSize:120 weight:UIFontWeightBold],
            NSForegroundColorAttributeName: UIColor.blackColor,
            NSParagraphStyleAttributeName: p,
        }];
    }];
}

static UIImage *TTCMakeImage(void) {
    gShot += 1;
    NSDictionary *env = NSProcessInfo.processInfo.environment;
    NSString *next = env[@"TAS_TEST_CAMERA_NEXT"];
    if (next.length) {
        NSString *path = [[NSString stringWithContentsOfFile:next encoding:NSUTF8StringEncoding error:nil]
            stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        [NSFileManager.defaultManager removeItemAtPath:next error:nil];
        if ([path hasPrefix:@"text:"]) {
            NSLog(@"[TasTestCamera] shot #%lu text %@", (unsigned long)gShot, path);
            return TTCTextImage([path substringFromIndex:5]);
        }
        UIImage *img = path.length ? [UIImage imageWithContentsOfFile:path] : nil;
        if (img) {
            NSLog(@"[TasTestCamera] shot #%lu from %@", (unsigned long)gShot, path);
            return img;
        }
    }
    NSString *dir = env[@"TAS_TEST_CAMERA_DIR"];
    if (dir.length) {
        NSArray *files = [[[NSFileManager.defaultManager contentsOfDirectoryAtPath:dir error:nil]
            filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:
                @"self ENDSWITH[c] '.jpg' OR self ENDSWITH[c] '.jpeg' OR self ENDSWITH[c] '.png'"]]
            sortedArrayUsingSelector:@selector(compare:)];
        if (files.count) {
            UIImage *img = [UIImage imageWithContentsOfFile:
                [dir stringByAppendingPathComponent:files[(gShot - 1) % files.count]]];
            if (img) return img;
        }
    }
    CGSize size = CGSizeMake(1600, 1200);
    UIGraphicsImageRendererFormat *fmt = [UIGraphicsImageRendererFormat defaultFormat];
    fmt.scale = 1;
    UIGraphicsImageRenderer *r = [[UIGraphicsImageRenderer alloc] initWithSize:size format:fmt];
    return [r imageWithActions:^(UIGraphicsImageRendererContext *ctx) {
        NSArray *colors = @[UIColor.systemBlueColor, UIColor.systemTealColor, UIColor.systemIndigoColor,
                            UIColor.systemGreenColor, UIColor.systemOrangeColor, UIColor.systemPurpleColor];
        [colors[(gShot - 1) % colors.count] setFill];
        UIRectFill(CGRectMake(0, 0, size.width, size.height));
        NSDateFormatter *df = [NSDateFormatter new];
        df.dateFormat = @"yyyy-MM-dd HH:mm:ss";
        NSString *label = env[@"TAS_TEST_CAMERA_LABEL"] ?: @"autotest";
        NSString *text = [NSString stringWithFormat:@"TasCorp autotest\n%@\nснимок №%lu\n%@",
                          label, (unsigned long)gShot, [df stringFromDate:NSDate.date]];
        NSMutableParagraphStyle *p = [NSMutableParagraphStyle new];
        p.alignment = NSTextAlignmentCenter;
        [text drawInRect:CGRectMake(60, 330, size.width - 120, size.height - 400) withAttributes:@{
            NSFontAttributeName: [UIFont boldSystemFontOfSize:90],
            NSForegroundColorAttributeName: UIColor.whiteColor,
            NSParagraphStyleAttributeName: p,
        }];
    }];
}

@interface TTCOverlay : UIView
@property (nonatomic, weak) UIImagePickerController *picker;
@end

@implementation TTCOverlay

- (instancetype)initWithPicker:(UIImagePickerController *)picker {
    if ((self = [super initWithFrame:UIScreen.mainScreen.bounds])) {
        _picker = picker;
        self.backgroundColor = UIColor.blackColor;
        self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        CGRect b = self.bounds;

        UILabel *title = [[UILabel alloc] initWithFrame:CGRectMake(0, b.size.height * 0.4, b.size.width, 40)];
        title.text = @"Тестовая камера (Simulator)";
        title.textColor = UIColor.whiteColor;
        title.textAlignment = NSTextAlignmentCenter;
        [self addSubview:title];

        UIButton *shutter = [UIButton buttonWithType:UIButtonTypeCustom];
        shutter.frame = CGRectMake((b.size.width - 76) / 2, b.size.height - 190, 76, 76);
        shutter.backgroundColor = UIColor.whiteColor;
        shutter.layer.cornerRadius = 38;
        shutter.accessibilityIdentifier = @"PhotoCapture";
        shutter.accessibilityLabel = @"Take Picture";
        [shutter addTarget:self action:@selector(shoot) forControlEvents:UIControlEventTouchUpInside];
        [self addSubview:shutter];

        UIButton *cancel = [UIButton buttonWithType:UIButtonTypeSystem];
        cancel.frame = CGRectMake(16, b.size.height - 170, 80, 36);
        [cancel setTitle:@"Cancel" forState:UIControlStateNormal];
        [cancel setTitleColor:UIColor.whiteColor forState:UIControlStateNormal];
        cancel.accessibilityIdentifier = @"Cancel";
        [cancel addTarget:self action:@selector(cancel) forControlEvents:UIControlEventTouchUpInside];
        [self addSubview:cancel];
    }
    return self;
}

- (void)shoot {
    UIImagePickerController *picker = self.picker;
    id<UIImagePickerControllerDelegate> delegate = (id)picker.delegate;
    if (![delegate respondsToSelector:@selector(imagePickerController:didFinishPickingMediaWithInfo:)]) return;
    UIImage *img = TTCMakeImage();
    NSMutableDictionary *info = [@{
        UIImagePickerControllerMediaType: @"public.image",
        UIImagePickerControllerOriginalImage: img,
        UIImagePickerControllerMediaMetadata: @{},
    } mutableCopy];
    if (picker.allowsEditing) {
        info[UIImagePickerControllerEditedImage] = img;
        info[UIImagePickerControllerCropRect] = [NSValue valueWithCGRect:CGRectMake(0, 0, img.size.width, img.size.height)];
    }
    NSLog(@"[TasTestCamera] shot #%lu %.0fx%.0f", (unsigned long)gShot, img.size.width, img.size.height);
    [delegate imagePickerController:picker didFinishPickingMediaWithInfo:info];
}

- (void)cancel {
    id<UIImagePickerControllerDelegate> delegate = (id)self.picker.delegate;
    if ([delegate respondsToSelector:@selector(imagePickerControllerDidCancel:)]) {
        [delegate imagePickerControllerDidCancel:self.picker];
    } else {
        [self.picker dismissViewControllerAnimated:YES completion:nil];
    }
}

@end

static void (*gOrigPresent)(id, SEL, UIViewController *, BOOL, id);

static void TTCPresent(UIViewController *self, SEL _cmd, UIViewController *vc, BOOL animated, id completion) {
    if ([vc isKindOfClass:UIImagePickerController.class]) {
        UIImagePickerController *picker = (UIImagePickerController *)vc;
        if (picker.sourceType == UIImagePickerControllerSourceTypeCamera) {
            NSLog(@"[TasTestCamera] camera picker intercepted");
            picker.showsCameraControls = NO;
            picker.cameraOverlayView = [[TTCOverlay alloc] initWithPicker:picker];
        }
    }
    gOrigPresent(self, _cmd, vc, animated, completion);
}

__attribute__((constructor)) static void TTCInit(void) {
    Method m = class_getInstanceMethod(UIViewController.class, @selector(presentViewController:animated:completion:));
    gOrigPresent = (void *)method_setImplementation(m, (IMP)TTCPresent);
    NSLog(@"[TasTestCamera] loaded");
}
