from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.joinpath("minimap_renderer/src")))

from renderer.render import Renderer, RenderDual
from replay_parser import ReplayParser

def render_single(replay_path): 
    input_path = Path(replay_path)
    output_path = input_path.parent.joinpath(f"{input_path.stem}.mp4")
    try:
        with open(replay_path, "rb") as f:
            replay_info = ReplayParser(
                f, strict=True, raw_data_output=False
            ).get_info()
        renderer = Renderer(
            replay_info["hidden"]["replay_data"],
            logs=True,
            enable_chat=True,
            use_tqdm=True,
        )
        renderer.start(str(output_path))
    except Exception as e:
        return -1, str(e)
    return 0, str(Path(output_path).resolve())

def render_dual(alpha_path, bravo_path):
    input_path1 = Path(alpha_path)
    input_path2 = Path(bravo_path)
    output_path = input_path1.parent.joinpath(f"{input_path1.stem} + {input_path2.stem}.mp4")
    try:
        with open(alpha_path, "rb") as f1, open(bravo_path, "rb") as f2:
            alpha_info = ReplayParser(
                f1, strict=True, raw_data_output=False
            ).get_info()
            bravo_info = ReplayParser(
                f2, strict=True, raw_data_output=False
            ).get_info()
            renderer = RenderDual(
                alpha_info["hidden"]["replay_data"],
                bravo_info["hidden"]["replay_data"],
                green_tag="Alpha",
                red_tag="Bravo",
                team_tracers=True,
            )
            renderer.start(str(output_path))
    except Exception as e:
        return -1, str(e)
    return 0, str(Path(output_path).resolve())
