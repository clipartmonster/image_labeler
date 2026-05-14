from django.core.management.base import BaseCommand
from label_images.models import RuleGuide, RuleDirective


RULES = [
    {
        "task_type": "asset_type",
        "rule_index": 1,
        "category": "Asset Type",
        "title": "Photograph or Photo-realistic",
        "description": (
            "Assets can\u2019t be a photograph or a photo-realistic 3d rendering."
        ),
        "directives": [
            "If the asset is a photograph label yes.",
            "If the asset is photo-realistic or a 3d rendering label yes.",
            "A detailed sketch is not photo-realistic.",
            "Black and white photos should be labeled as photo-realistic.",
            "Abstract backgrounds that look realistic should be labeled yes.",
            "Detailed control panel/infographic is labeled no.",
            "Background can be mostly flat.",
            "An asset with a photograph background but with non-photograph main elements are still considered photographs.",
            "An asset with a photo or photo-realistic main element and non photograph background is labeled as photograph.",
        ],
    },
    {
        "task_type": "asset_type",
        "rule_index": 3,
        "category": "Asset Type",
        "title": "External Text",
        "description": (
            "External words refer to the presence of text not contained in the main elements. "
            "Often used to describe the image, describe a feature, or to block out marketing or educational copy. "
            "Common in poster, brochure and logo designs. External words do not have to be in English."
        ),
        "directives": [
            "Photos never have external text.",
            "Words contained in the main element that don\u2019t normally go there are external.",
            "Words contained in a banner and serves as title and or copy are external.",
            "External words cannot be contained in the main element(s).",
            "Words on maps are not external text. Words as a title on a map are external.",
            "External words are often found on designs.",
            "External words often characterized features and design attributes of the art.",
            "Free standing text in clip art packs are external words.",
            "External words can include non-English words.",
            "Single letters, even those with additional design work are considered external words.",
            "Microstock names watermarked on image are not external text.",
            "Text in speech bubbles is not external text.",
            "Text in a logo is external text.",
        ],
    },
    {
        "task_type": "asset_type",
        "rule_index": 5,
        "category": "Asset Type",
        "title": "Multiple Main Elements",
        "description": (
            "An asset with more than one main asset has multiple main elements."
        ),
        "directives": [
            "Multiple main elements must have more than one main element.",
            "Multiple main elements that are identical to each other are not multiple main elements.",
            "Multiple main elements must not obscure each other.",
            "Multiple main elements can be variations of the same art.",
            "Infographics with multiple main elements do not count.",
            "Two main elements obscuring each other may be a composite of two minor elements forming a single main element.",
            "Multiple main elements must have some separation between each other.",
            "Multiple main elements that are alphabet or number set always counts.",
            "A main element accompanied with some text only counts as one main element.",
            "Pamphlets, brochures and menu pages with multiple pages count as multiple elements.",
            "Main elements that form a shape or their design are not multiple main elements.",
            "Multiple main elements interacting in a scene do not count as multiple main elements.",
            "Worksheet with many main elements do not count as multiple main elements.",
        ],
    },
    {
        "task_type": "asset_type",
        "rule_index": 6,
        "category": "Asset Type",
        "title": "Separability",
        "description": (
            "Main elements that can easily be extracted from the rest of the image are separable."
        ),
        "directives": [
            "Must have a main element.",
            "Main element must be surrounded by a blank color.",
            "Minor elements that make up a main element must all be separable.",
            "If there are multiple main elements, they need to be separated from each other so that each one can be easily extracted.",
            "Assets that are photographs are never separable.",
            "Assets with illustrated backgrounds are never separable.",
            "Patterns with repeating main elements that are cropped are not separable.",
            "The main element can be cropped but the crop can\u2019t extend across an entire side of the image.",
            "Main elements inside a scene but with a static color border (or frame) are separable.",
        ],
    },
    {
        "task_type": "asset_type",
        "rule_index": 7,
        "category": "Asset Type",
        "title": "Pattern",
        "description": (
            "Repeating Elements refers to when the main and minor element(s) are repeating across the asset. "
            "Usually the repeating main element(s) are consistently spaced in an organized manner."
        ),
        "directives": [
            "Repeating elements must be identical to each other.",
            "Repeating element may not contain a main element but instead design elements like rectangles, circles or other shapes.",
            "The main element may continue from one edge of the asset to the other side to create a seamless pattern.",
            "A main element may not repeat as long as it continues from one edge to the other edge to form a seamless pattern and still be labeled repeatable.",
            "An asset with a vertical or horizontal segment repeating with another segment just text for a title or product description is still considered repeating.",
            "Repeating patterns in a pack are labeled as repeating patterns.",
        ],
    },
    {
        "task_type": "clip_art_type",
        "rule_index": 1,
        "category": "Clip Art Type",
        "title": "Mono-Color",
        "description": "Clip art that has only one color.",
        "directives": [
            "An asset is labeled mono-color when the lines and fills are all one color.",
            "An asset with multiple main elements can be mono-color as long as each main element is only one color.",
            "Common for mono-color to be a black and white clip art but can be any color including white.",
            "Assets with a gradient background design element but solid color main element are labeled mono-color.",
            "Assets with a background design element in a different color but a main element in only one color is labeled mono-color.",
            "Assets with a background design element in a different color but a main element with a fill in one color and outline in another color is labeled as mono-color.",
            "Gradients even when subtle are not mono-color.",
            "Main elements filled with a mono-color gradient are not mono-color.",
            "Main element filled with hatching or dots that creates gradients in one color are NOT mono-color.",
            "Main elements filled with hatching or dots that does not create a gradient effect ARE mono-color.",
            "Minor or design elements with a different color labels the asset as NOT mono-color.",
            "Design elements detailing features of the asset in a different color are NOT mono-color.",
            "Outline in front of a gradient design element is mono color if the outline is only one color.",
            "If there are two assets, identical in line art, defer to the color version.",
            "Assets with a solid fill but drop shadow in one direction are not mono color.",
        ],
    },
    {
        "task_type": "multi_color_type",
        "rule_index": 1,
        "category": "Multi Color Type",
        "title": "Fill Segmentation",
        "description": (
            "When a clip art\u2019s internal segments are defined by variation in the colors they are filled with. "
            "Adjacent internal sections \u2013 or segments \u2013 must have different colors that form the internal shape of the clip art. "
            "As for mono-color fill segmentation is characterized by one color with smooth or rough fills. "
            "Sketches can be filled with cross hatch to show fill segmentation. "
            "Mono-color clipart can be intermixed with smooth one color fill adjacent to smooth negative spaces."
        ),
        "directives": [
            "Fills defining the boundary of internal segments can not overlap.",
            "External lines are permitted as long as they don\u2019t help form the clip art\u2019s internal segments.",
            "Assets with internal lines that do not help form the segments of the clip art do not exclude the asset from being labeled as fill boundary.",
            "Filled segments have clear edges that make it easy to see the different segments.",
        ],
    },
    {
        "task_type": "mono_color_type",
        "rule_index": 2,
        "category": "Mono Color Type",
        "title": "Line Segmentation (Mono-Color)",
        "description": (
            "When a clip art\u2019s internal segments are defined by lines. "
            "A clip art is still segmented by line even when the line width varies across the asset."
        ),
        "directives": [
            "Use only lines that delineate the boundaries of the main element\u2019s segments. Internal or external lines that don\u2019t define the boundaries of segments should be ignored when labelling whether an asset has line segmentation.",
            "Outline lines framing the boundaries of the asset are labeled as line segments.",
            "Thin inverted lines that form boundaries are not labeled as line segments.",
            "Thick inverted lines that form boundaries are not labeled as line segments.",
            "If portions of the asset have boundaries delineated both lines and fills then the asset is labeled as a line segmentation (the asset will be labeled as fill segmentation too).",
            "Detailed sketches that have some lines helping form the boundary are labeled with line segmentation.",
        ],
    },
    {
        "task_type": "multi_color_type",
        "rule_index": 2,
        "category": "Multi Color Type",
        "title": "Line Segmentation (Multi-Color)",
        "description": (
            "When a clip art\u2019s internal segments are defined by lines."
        ),
        "directives": [
            "Lines must form internal segments of the clip art.",
            "Lines forming different segments can be different colors.",
            "External lines do not count as segments but are permitted.",
            "Internal lines that do not form an internal boundary are not segments but are permitted.",
            "A line segment forming a boundary does not have to conform to the underlying color fill.",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed RuleGuide and RuleDirective records from the predefined rule set."

    def handle(self, *args, **options):
        created_guides = 0
        created_directives = 0

        for idx, rule in enumerate(RULES):
            guide, was_created = RuleGuide.objects.update_or_create(
                task_type=rule["task_type"],
                rule_index=rule["rule_index"],
                defaults={
                    "title": rule["title"],
                    "category": rule["category"],
                    "description": rule["description"],
                    "display_order": idx,
                },
            )
            if was_created:
                created_guides += 1

            for num, text in enumerate(rule["directives"], start=1):
                _, d_created = RuleDirective.objects.update_or_create(
                    guide=guide,
                    number=num,
                    defaults={"text": text},
                )
                if d_created:
                    created_directives += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {created_guides} guides created, {created_directives} directives created."
            )
        )
