import kivy.uix.image
from kivy.app import App
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import mainthread
from kivy.factory import Factory
from pathlib import Path
import shutil
from PIL import Image
from random import choices, shuffle
from collections import Counter
from os.path import join
import json
import threading


class RootWidget(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    TOTAL_POSSIBILITIES = 1
    IMAGES_PATH = ""

    @staticmethod
    def error_popup(title, content) -> None:
        close_button = Button(text='Close', size_hint=(1, .1))
        content_box = BoxLayout(orientation='vertical')
        content_box.add_widget(content)
        content_box.add_widget(close_button)
        error_popup = Popup(title=title, title_color='red',
                            content=content_box,
                            title_align='center', size_hint=(.6, .6), auto_dismiss=False)
        close_button.bind(on_press=error_popup.dismiss)
        error_popup.open()

    def verify_selected_folder(self, icon_view, popup):
        def inner_func(instance):
            if len(icon_view.selection) == 0:
                title = 'No Folder Selected'
                content = Factory.ErrorLabel(
                    text='You must select a folder!.')
                RootWidget.error_popup(title, content)
                return
            if not Path(icon_view.selection[0]).is_dir():
                title = 'File Selected!'
                content = Factory.ErrorLabel(text='Only folders can be selected.')
                RootWidget.error_popup(title, content)
                return

            image_sizes = set()
            layer_dirs = list(Path(icon_view.selection[0]).iterdir())
            # We check if the layer folder contains a sufficient number of layers.
            num_layers = 0
            for obj in layer_dirs:
                if obj.is_dir():
                    num_layers += 1
            if num_layers < 2:
                title = 'Insufficient number of layers!'
                content = Factory.ErrorLabel(text=f'{Path(icon_view.selection[0]).name} contains an insufficient number'
                                                  f' of layers, at least 2 layers are expected')
                RootWidget.error_popup(title, content)
                return
            # We check if the path to the layer directories strictly consists of PNG image files
            for layer_dir in layer_dirs:
                files = list(layer_dir.iterdir())
                RootWidget.TOTAL_POSSIBILITIES *= len(files)
                for file in files:
                    if file.suffix != '.png':
                        title = 'Wrong File Format Discovered!'
                        content = Factory.ErrorLabel(text=f'{file.name} in the {layer_dir.name}'
                                                          f' folder is not a PNG image file!')
                        RootWidget.error_popup(title, content)
                        return
                    img = Image.open(file)
                    image_sizes.add(img.size)

            # We check if the PNG images all have the same size in pixels.
            if len(image_sizes) != 1:
                title = 'Trait Images Are Not of Equal Size!'
                content = Factory.ErrorLabel(text=f'All trait images must have the same size')
                RootWidget.error_popup(title, content)
                return

            # We check if the weights in the .png file names are actually numerical values.
            for layer_dir in layer_dirs:
                for file in layer_dir.iterdir():
                    weight = file.stem.split(" ")[-1]
                    try:
                        float(weight)
                    except ValueError:
                        title = 'Numerical Value Expected, Non-numerical value given!'
                        content = Factory.ErrorLabel(text=f'"{weight}" in "{file.name}" is NOT a numerical value.')
                        RootWidget.error_popup(title, content)
            RootWidget.IMAGES_PATH = icon_view.selection[0]
            self.sm.get_screen('main_screen').folder_selector.text = 'Layers Folder Selected'
            popup.dismiss()
        return inner_func

    def select_images_folder(self) -> None:
        confirm_button = Button(text='Confirm Selection', size_hint=(1, .1))
        image_dir_selector = FileChooserIconView(dirselect=True, multiselect=False)
        content_box = BoxLayout(orientation='vertical')
        content_box.add_widget(image_dir_selector)
        content_box.add_widget(confirm_button)
        file_selector_popup = Popup(title='Select Layers Folder', title_color='white',
                                    content=content_box, title_align='center',
                                    size_hint=(.85, .85), auto_dismiss=False)
        confirm_button.bind(on_press=self.verify_selected_folder(image_dir_selector, file_selector_popup))
        file_selector_popup.open()

    def is_valid_input(self) -> bool:
        layers_input = self.sm.get_screen('main_screen').layers.text.strip('"" \n')
        supply = self.sm.get_screen('main_screen').supply.text.strip('"" \n')
        retrieval_path = RootWidget.IMAGES_PATH

        # We check if all text input boxes are non-empty, if this not the case, a popup containing an error message is
        # displayed to the user
        if layers_input == '':
            title = 'Text input box must not be empty!'
            content = Factory.ErrorLabel(
                text='The layers input box is empty, please fill it in appropriately as described in the tips section.')
            RootWidget.error_popup(title, content)
            return False

        if supply == '':
            title = 'Text input box must not be empty!'
            content = Factory.ErrorLabel(
                text='The supply input box is empty, please enter the number of NFT images you wish to generate.')
            RootWidget.error_popup(title, content)
            return False

        if retrieval_path == '':
            title = 'Text input box must not be empty!'
            content = Factory.ErrorLabel(
                text='The retrieval path text input box is empty, please select the folder containing '
                     'the nft images')
            RootWidget.error_popup(title, content)
            return False

        # We check if the number of layer names supplied by the user is equivalent to the number of layer directories
        # in the directory that `retrieval path` points to.
        layers = layers_input.split('\n')
        layer_dirs = list(Path(retrieval_path).iterdir())
        if len(layer_dirs) != len(layers):
            title = 'User Error!'
            content = Factory.ErrorLabel(text=f'Expected {len(layer_dirs)} layer names, got {len(layers)} '
                                              f'layer names instead.')
            RootWidget.error_popup(title, content)
            return False

        # We check if all the supplied layer names are actually directory names.
        for layer_name in layers:
            layer_path = Path(retrieval_path)/layer_name
            if not layer_path.is_dir():
                title = 'Folder not found!.'
                content = Factory.ErrorLabel(text=f'The folder "{layer_path}", does not exist.')
                RootWidget.error_popup(title, content)
                return False

        # We check if it is possible to generate the requested number of nft images.
        if int(supply) > RootWidget.TOTAL_POSSIBILITIES:
            title = 'Impossible Request!'
            content = Factory.ErrorLabel(text=f'You cannot generate more than {RootWidget.TOTAL_POSSIBILITIES} images.'
                                              f'\nPlease enter a number less than or equal to this value and try again.')
            RootWidget.error_popup(title, content)
            return False

        return True

    def generate_nft_images(self, nft, layers, retrieval_path_str, save_to_path_str, lock, nft_traits_to_id,
                            num_gen_images, imagepath_list, all_image_traits, total_supply) -> None:

        retrieval_path = Path(retrieval_path_str)
        save_to_path = Path(save_to_path_str)
        token_id = nft_traits_to_id[nft]
        nft_traits = nft.split("|||")
        trait_paths = []
        for i in range(len(layers)):
            trait_path = retrieval_path/f"{layers[i]}/{nft_traits[i]}.png"
            trait_paths.append(trait_path)

        if len(layers) == 2:
            img1 = Image.open(trait_paths[0])
            img1_con = img1.convert("RGBA")
            img2 = Image.open(trait_paths[1])
            img2_con = img2.convert("RGBA")
            nft_image = Image.alpha_composite(img1_con, img2_con)
            nft_image.save(save_to_path/f"{token_id}.png")

        elif len(layers) >= 3:
            img1 = Image.open(trait_paths[0])
            img1_con = img1.convert("RGBA")
            img2 = Image.open(trait_paths[1])
            img2_con = img2.convert("RGBA")
            composite = Image.alpha_composite(img1_con, img2_con)
            trait_paths_slice = trait_paths[2:]
            for i in range(len(trait_paths_slice)):
                img = Image.open(trait_paths_slice[i])
                img_con = img.convert("RGBA")
                composite = Image.alpha_composite(composite, img_con)
            composite.save(save_to_path/f"{token_id}.png")

            if len(imagepath_list) < 20:
                imagepath_list.append(save_to_path/f"{token_id}.png")

        image_traits = RootWidget.get_image_traits(nft, layers, token_id)
        with lock:
            num_gen_images["num_gen_images"] += 1
            num_images_gen = num_gen_images["num_gen_images"]
            all_image_traits.append(image_traits)
            percent = (num_images_gen / total_supply) * 100
            self.update_screen(percent, num_images_gen, total_supply)

    def generate_nft_images_thread(self, nfts, layers, retrieval_path_str, save_to_path_str, lock, nft_traits_to_id,
                                   num_gen_images, total_supply, imagepath_list, all_image_traits) -> None:
        for nft in nfts:
            self.generate_nft_images(nft, layers, retrieval_path_str, save_to_path_str, lock, nft_traits_to_id,
                                     num_gen_images, imagepath_list, all_image_traits, total_supply)

    @staticmethod
    def get_image_traits(nft_string, layers, token_id) -> dict:
        trait_dict = {}
        image_traits = nft_string.split("|||")
        for i in range(len(image_traits)):
            image_traits[i] = " ".join(image_traits[i].split()[:-1])
        trait_dict["tokenId"] = token_id
        for i in range(len(layers)):
            trait_dict[layers[i]] = image_traits[i]
        return trait_dict

    @staticmethod
    def gif_generator(imagepath_list, gif_path) -> None:
        image_list = []
        for path in imagepath_list:
            image = Image.open(path).copy()
            image_list.append(image)
        shuffle(image_list)
        image_list[0].save(Path(gif_path)/"GIF.gif", save_all=True, append_images=image_list[1:], optimize=False,
                           disposal=2, duration=550, loop=0)

    @staticmethod
    def sort_key(file_name: str) -> float:
        weight = float(file_name.split()[-1])
        return weight

    @staticmethod
    def generate_rarity_table(nfts, rarity_table_dir, categories, layers, totalsupply) -> None:

        rarity_file = open(Path(rarity_table_dir)/"Rarity_Table.txt", "w")
        text = "Rarity Table".center(59)
        rarity_file.write(text + "\n" * 3)

        store = []
        for nft in nfts:
            nft_traits = nft.split("|||")
            store.extend(nft_traits)

        alltraits_tally_dict = Counter(store)
        categories_copy = categories.copy()
        for i in range(len(categories_copy)):
            categories_copy[i].sort(key=RootWidget.sort_key)
        for i in range(len(categories_copy)):
            percentsum = 0
            category_name = f"{layers[i]} Traits".center(55)
            rarity_file.write(category_name + "\n" * 2)
            for j in range(len(categories_copy[i])):
                trait = categories_copy[i][j]
                trait_tally = alltraits_tally_dict[trait]
                trait_percent = (trait_tally / totalsupply) * 100
                percentsum += trait_percent
                rarity_file.write(f"{' '.join(trait.split()[:-1])}	{trait_percent:0.2f}%\n")
            rarity_file.write(f"Percentage sum for this category is {percentsum:0.2f}%")
            rarity_file.write("\n" * 3)

        rarity_file.close()

    @mainthread
    def update_screen(self, percent, num_images, totalsupply) -> None:
        gen_screen = self.sm.get_screen('gen_screen')
        gen_screen.progress_bar.value = percent
        gen_screen.progress_text.text = f'Generated {num_images} images out of {totalsupply} images'

    @mainthread
    def on_gen_comp(self, save_to_path, totalsupply) -> None:
        if totalsupply <= 35:
            loop_var = totalsupply
        else:
            loop_var = 35

        image_layout = self.sm.get_screen('gen_comp_screen').image_layout
        for num in range(1, loop_var + 1):
            source = Path(save_to_path)/f"{num}.png"
            image_button = ImageButton(source=source.__str__())
            image_layout.add_widget(image_button)

        self.menu_actionbar.disabled = False
        self.sm.current = 'gen_comp_screen'

    def second_thread(self) -> None:
        layers = self.sm.get_screen('main_screen').layers.text.strip('"" \n').split('\n')
        totalsupply = int(self.sm.get_screen('main_screen').supply.text)
        retrieval_path = RootWidget.IMAGES_PATH

        categories = []
        allweights = []
        layers_to_traits = {}
        layers_to_weights = {}
        layer_dirs = list(Path(retrieval_path).iterdir())
        for layer_dir in layer_dirs:
            files = list(layer_dir.iterdir())
            traits = []
            weights = []
            for file in files:
                trait_data = file.stem.split(' ')
                trait = file.stem
                weight = float(trait_data[-1])
                traits.append(trait)
                weights.append(weight)
            layers_to_traits[layer_dir.name] = traits
            layers_to_weights[layer_dir.name] = weights

        for layer in layers:
            categories.append(layers_to_traits[layer])
            allweights.append(layers_to_weights[layer])


        l = "/"
        if "\\" in retrieval_path:
            l = "\\"

        general_path = retrieval_path.split(l)[:-1]
        general_path = f"{l}".join(general_path)

        app_output_dir = f'{general_path}{l}Gener8 App Output'
        try:
            Path(app_output_dir).mkdir()
        except FileExistsError:
            shutil.rmtree(app_output_dir)
            Path(app_output_dir).mkdir()
        save_to_path = f'{app_output_dir}{l}NFT Images'
        Path(save_to_path).mkdir(exist_ok=True)

        nfts = set()
        token_id = 1
        all_image_traits = []
        imagepath_list = []
        nft_traits_to_id = {}
        num_nfts = 0

        while num_nfts < totalsupply:
            nft = []
            for i in range(len(categories)):
                trait = choices(categories[i], weights=allweights[i], k=1)
                trait = "".join(trait)
                nft.append(trait)

            nft_string = "|||".join(nft)
            if nft_string not in nfts:
                nfts.add(nft_string)
                nft_traits_to_id[nft_string] = token_id
                token_id += 1
                num_nfts += 1

        threads = []
        nfts_list = list(nfts)
        NUM_THREADS = 15
        nft_per_slice = num_nfts // NUM_THREADS
        rem = num_nfts % NUM_THREADS
        first_idx = 0
        lock = threading.Lock()
        num_gen_images = {"num_gen_images": 0}
        for i in range(1, NUM_THREADS + 1):
            last_idx = i * nft_per_slice
            if i == NUM_THREADS:
                last_idx += rem
            thread_nfts = nfts_list[first_idx:last_idx]
            thread = threading.Thread(target=self.generate_nft_images_thread, args=(thread_nfts, layers, retrieval_path,
                save_to_path, lock, nft_traits_to_id, num_gen_images, totalsupply, imagepath_list, all_image_traits),
                daemon=True)
            threads.append(thread)
            thread.start()
            first_idx = last_idx
        for thread in threads:
            thread.join()

        all_image_traits.append(app_output_dir)
        all_nfts_metadata = App.get_running_app().storage
        with open(all_nfts_metadata, 'w') as output_file:
            json.dump(all_image_traits, output_file, indent=4)

        # We generate a rarity table, which is a table that shows the percentage occurrence of each trait in the nft
        # collection. This instantly enables the user and any other person to see how rare each trait in the
        # collection is.
        rarity_table_dir = f'{app_output_dir}{l}Rarity Table'
        Path(rarity_table_dir).mkdir(exist_ok=True)
        RootWidget.generate_rarity_table(nfts, rarity_table_dir, categories, layers, totalsupply)

        gif_path = f"{app_output_dir}{l}GIF"
        Path(gif_path).mkdir(exist_ok=True)
        RootWidget.gif_generator(imagepath_list, gif_path)

        self.on_gen_comp(save_to_path, totalsupply)

    def on_generate_images(self) -> None:
        if self.is_valid_input():
            self.sm.current = 'gen_screen'
            self.menu_actionbar.disabled = True
            threading.Thread(target=self.second_thread, daemon=True).start()

    def is_valid_third_thread_input(self) -> bool:
        extra_metadata_input = self.sm.get_screen('metadata_screen').extra_metadata.text.strip('"" \n')
        base_image_url = self.sm.get_screen('metadata_screen').base_image_url.text.strip('""/')
        collection_name = self.sm.get_screen('metadata_screen').collection_name.text.strip('"" ')
        if base_image_url == '':
            title = 'Base image URL input box must NOT be empty!'
            content = Factory.ErrorLabel(text='Please fill in the base image URL input box appropriately as described '
                                              'in the Tips section.')
            RootWidget.error_popup(title, content)
            return False
        if extra_metadata_input != '':
            extra_metadata = extra_metadata_input.split('\n')
            for info in extra_metadata:
                if len(info.split('=')) < 2:
                    title = 'User Error!'
                    content = Factory.ErrorLabel(text=f'"{info}" is not properly formatted. Please see the '
                                                      f'Tips section for more information.')
                    RootWidget.error_popup(title, content)
                    return False
        if collection_name == '':
            title = 'Collection name input box must NOT be empty!'
            content = Factory.ErrorLabel(text='Please fill in the collection name input box appropriately as described '
                                              'in the Tips section.')
            RootWidget.error_popup(title, content)
            return False
        if not Path(App.get_running_app().storage).exists():
            title = 'Stored partial metadata file could NOT be found!'
            content = Factory.ErrorLabel(text='Partial metadata file stored on this device could NOT be found.\n\n'
                                              'Likely Reasons:\nDeletion of this file.\nYour NFT collection images '
                                              'has not yet been generated.\n\nThis file is needed in order to generate '
                                              'the metadata of the NFTs in your collection.\nThe only solution to '
                                              'this issue is to regenerate your collection images.')
            RootWidget.error_popup(title, content)
            return False

        all_metadata = open(App.get_running_app().storage, 'r')
        try:
            json.load(all_metadata)
        except json.JSONDecodeError:
            title = 'Stored partial metadata file is empty!'
            content = Factory.ErrorLabel(text='Partial metadata file stored on this device is empty.\nThe data in this '
                                              'file is needed in order to generate the metadata data of the NFTs in '
                                              'your collection.\nThe only solution to this issue is to regenerate your '
                                              'collection images.')
            RootWidget.error_popup(title, content)
            return False

        return True

    def third_thread(self) -> None:
        extra_metadata_input = self.sm.get_screen('metadata_screen').extra_metadata.text.strip('"" \n')
        base_image_url = self.sm.get_screen('metadata_screen').base_image_url.text.strip('""/')
        collection_name = self.sm.get_screen('metadata_screen').collection_name.text.strip('"" ')

        all_metadata = open(App.get_running_app().storage, 'r')
        data = json.load(all_metadata)
        app_output_dir = data.pop(-1)
        nft_metadata_dir = Path(app_output_dir) / 'NFT Metadata'
        try:
            nft_metadata_dir.mkdir(parents=True)
        except FileExistsError:
            shutil.rmtree(nft_metadata_dir)
            nft_metadata_dir.mkdir()

        index = 0
        num_files = len(data)
        for dictt in data:
            token_id = dictt["tokenId"]
            token = {
                "name": f"{collection_name} #{token_id}",
                "image": f"{base_image_url}/{token_id}.png",
                "tokenId": token_id
            }
            if extra_metadata_input != '':
                extra_metadata = extra_metadata_input.split('\n')
                for info in extra_metadata:
                    field = info.split('=')[0]
                    value = "=".join(info.split('=')[1:])
                    token[field] = value
            token["attributes"] = []

            for key in dictt:
                if key != "tokenId":
                    token["attributes"].append({"trait_type": key,
                                                "value": dictt[key]
                                                })
            metadata_file = nft_metadata_dir/f'{token_id}.json'
            metadata_file.touch()
            with metadata_file.open(mode="w") as output_file:
                json.dump(token, output_file, indent=4)
            index += 1
            percent = (index / num_files) * 100
            self.update_metadata_gen_screen(percent, index, num_files)

        all_metadata.close()

    @mainthread
    def update_metadata_gen_screen(self, percent, index, num_files) -> None:
        gen_screen = self.sm.get_screen('metadata_gen_screen')
        gen_screen.progress_bar.value = percent
        gen_screen.progress_text.text = f'Generated {index} metadata files out of {num_files} metadata files.'

    def on_generate_metadata(self) -> None:
        if self.is_valid_third_thread_input():
            self.sm.current = 'metadata_gen_screen'
            self.menu_actionbar.disabled = True
            thread = threading.Thread(target=self.third_thread, daemon=True)
            thread.start()
            thread.join()
            self.menu_actionbar.disabled = False
            self.sm.current = 'metadata_gen_comp_screen'






class ImageButton(ButtonBehavior, kivy.uix.image.Image):
    def __int__(self, source, **kwargs):
        super(ImageButton, self).__init__(**kwargs)
        self.source = source
        self.allow_stretch = True
        self.keep_ratio = False

    def on_press(self):
        title = Path(self.source).name
        image_popup = Popup(title=title, title_color='white',
                            content=kivy.uix.image.Image(source=self.source),
                            title_align='center', size_hint=(.8, .8), auto_dismiss=True)
        image_popup.open()


class Gener8App(App):

    def build(self):
        return RootWidget()

    @property
    def storage(self):
        return join(self.user_data_dir, 'all_image_traits.json')


if __name__ == "__main__":
    Gener8App().run()
