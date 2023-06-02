from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.joinpath("minimap_renderer/src")))

from typing import Any, Callable, Optional
from PIL import Image, ImageDraw
from tqdm import tqdm
from layers_modified.chat_multilingual import LayerChatBase
from layers_modified.frag_moved import LayerFragBase
from renderer.render import Renderer, RenderDual
from replay_parser import ReplayParser

class myRenderer(Renderer):
    def start(
        self,
        path: str,
        fps: int = 20,
        quality: int = 7,
        progress_cb: Optional[Callable[[float], Any]] = None,
    ):
        """Starts the rendering process"""
        self._check_if_operations()
        self._load_map()

        assert self.minimap_fg
        assert self.minimap_bg

        layer_ship = self._load_layer("LayerShip")(self)
        layer_shot = self._load_layer("LayerShot")(self)
        layer_torpedo = self._load_layer("LayerTorpedo")(self)
        layer_smoke = self._load_layer("LayerSmoke")(self)
        layer_plane = self._load_layer("LayerPlane")(self)
        layer_ward = self._load_layer("LayerWard")(self)
        layer_building = self._load_layer("LayerBuilding")(self)
        layer_capture = self._load_layer("LayerCapture")(self)
        layer_health = self._load_layer("LayerHealth")(self)
        layer_score = self._load_layer("LayerScore")(self)
        layer_counter = self._load_layer("LayerCounter")(self)
        # layer_frag = self._load_layer("LayerFrag")(self)
        layer_frag = LayerFragBase(self)
        layer_timer = self._load_layer("LayerTimer")(self)
        layer_ribbon = self._load_layer("LayerRibbon")(self)
        # layer_chat = self._load_layer("LayerChat")(self)
        layer_chat = LayerChatBase(self)
        layer_markers = self._load_layer("LayerMarkers")(self)

        video_writer = self.get_writer(path, fps, quality)
        video_writer.send(None)

        self._draw_header(self.minimap_bg)
        last_key = list(self.replay_data.events)[-1]

        if self.use_tqdm:
            prog = tqdm(self.replay_data.events.keys())
        else:
            prog = self.replay_data.events.keys()

        total = len(prog)
        last_per = 0.0

        for idx, game_time in enumerate(prog):
            if progress_cb:
                per = round((idx + 1) / total, 1)
                if per > last_per:
                    last_per = per
                    progress_cb(per)

            minimap_img = self.minimap_fg.copy()
            minimap_bg = self.minimap_bg.copy()

            draw = ImageDraw.Draw(minimap_img)
            self.conman.update(game_time)

            if not self.is_operations:
                layer_capture.draw(game_time, minimap_img)
                layer_score.draw(game_time, minimap_bg)

            layer_building.draw(game_time, minimap_img)
            layer_ward.draw(game_time, minimap_img)
            layer_markers.draw(game_time, minimap_img)
            layer_shot.draw(game_time, minimap_img)
            layer_torpedo.draw(game_time, draw)
            layer_ship.draw(game_time, minimap_img)
            layer_smoke.draw(game_time, minimap_img)
            layer_plane.draw(game_time, minimap_img)
            layer_timer.draw(game_time, minimap_bg)

            if self.logs:
                layer_health.draw(game_time, minimap_bg)
                layer_counter.draw(game_time, minimap_bg)
                layer_frag.draw(game_time, minimap_bg)

                layer_ribbon.draw(game_time, minimap_bg)
                if self.enable_chat:
                    layer_chat.draw(game_time, minimap_bg)

            self.conman.tick()

            if game_time == last_key:
                img_win = Image.new("RGBA", self.minimap_fg.size)
                drw_win = ImageDraw.Draw(img_win)
                font = self.resman.load_font("warhelios_bold.ttf", size=48)
                player = self.replay_data.player_info[
                    self.replay_data.owner_id
                ]

                team_id = self.replay_data.game_result.team_id

                match team_id:
                    case a if a == player.team_id and a != -1:
                        text = "VICTORY"
                    case a if a != player.team_id and a != -1:
                        text = "DEFEAT"
                    case _:
                        text = "DRAW"

                tw, th = map(lambda i: i / 2, font.getbbox(text)[2:])
                mid_x, mid_y = map(lambda i: i / 2, minimap_img.size)
                offset_y = 6
                px, py = mid_x - tw, mid_y - th - offset_y

                for i in range(3 * fps):
                    per = min(1, i / (1.5 * fps))
                    drw_win.text(
                        (px, py),
                        text=text,
                        font=font,
                        fill=(255, 255, 255, round(255 * per)),
                        stroke_width=4,
                        stroke_fill=(*self.bg_color[:3], round(255 * per)),
                    )

                    minimap_img = Image.alpha_composite(minimap_img, img_win)
                    minimap_bg.paste(minimap_img, (40, 90))
                    video_writer.send(minimap_bg.tobytes())
            else:
                minimap_bg.paste(minimap_img, (40, 90))
                video_writer.send(minimap_bg.tobytes())
        video_writer.close()




def render_single(replay_path): 
    input_path = Path(replay_path)
    output_path = input_path.parent.joinpath(f"{input_path.stem}.mp4")
    try:
        with open(replay_path, "rb") as f:
            replay_info = ReplayParser(
                f, strict=True, raw_data_output=False
            ).get_info()
        renderer = myRenderer(
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
