#!/usr/bin/env python

import math
import random
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
from pprint import pprint


URL = 'http://www.robotreboot.com/classic'

RGB_MAP = {
    (85,85,255): 'blue',
    (252,255,31): 'yellow',
    (0,142,0): 'green'
}



def get_distance(a, b):
    # https://www.w3resource.com/python-exercises/python-basic-exercise-40.php
    #p1 = [4, 0]
    #p2 = [6, 6]
    #math.sqrt( ((p1[0]-p2[0])**2)+((p1[1]-p2[1])**2) )
    dist = math.sqrt(
        ((a[0] - b[0]) ** 2)
        +
        ((a[1] - b[1]) ** 2)
    )
    return dist


def is_opposite_direction(a,b):

    if sorted([a, b]) == ['left', 'right']:
        return True
    if sorted([a, b]) == ['down', 'up']:
        return True

    return False


def style_to_color(em):
    style = em.get_attribute('style')

    if 'darkorange' in style:
        return  'yellow'

    if 'rgb' in style:
        rgb = style.split(':')[-1].replace('rgb', '').replace(';', '')
        try:
            rgb = eval(rgb)
        except Exception as e:
            print(e)
            import epdb; epdb.st()
        color = RGB_MAP[rgb]
    else:
        color = style.split(':')[-1].replace(';','').strip()
    
    return color


def get_style_map(em):
    styletxt = em.get_attribute('style')
    styles = [x.strip() for x in styletxt.split(';') if x.strip()]
    sdict = {}
    for style in styles:
        sparts = [x.strip() for x in style.split(':')]
        sdict[sparts[0]] = sparts[1]
    return sdict


def get_style_key(em, key):
    sdict = get_style_map(em)
    return sdict[key]



class Robot:

    def __init__(self, driver, container):
        self.container = container
        self.driver = driver
    
    def click(self):
        self.container.click()

    @property
    def color(self):
        robot = self.container.find_element_by_class_name('robot')
        return style_to_color(robot)

    @property
    def top(self):
        pixel = get_style_key(self.container, 'top')
        val = int(pixel.replace('px', ''))
        return val

    @property
    def left(self):
        pixel = get_style_key(self.container, 'left')
        val = int(pixel.replace('px', ''))
        return val
    
    @property
    def coord(self):
        return (self.top, self.left)

    @property
    def arrows(self):
        arrows = {}
        for div in self.container.find_elements_by_class_name('arrow'):
            arrow = Arrow(self.driver, div, self)
            arrows[arrow.direction] = arrow
        return arrows


class Goal(Robot):
    
    @property
    def color(self):
        i = self.container.find_element_by_tag_name('i')
        return style_to_color(i)


class Arrow(Robot):

    def __init__(self, driver, container, parent):
        self.driver = driver
        self.container = container
        self.parent = parent

    @property
    def direction(self):
        classes = self.container.get_attribute('class')
        direction = classes.split()[-1].replace('arrow-', '')
        return direction   

    @property
    def distance(self):

        sdict = get_style_map(self.container)

        # invalid direction?
        if 'width' not in sdict or 'height' not in sdict:
            return 0

        vals = [
            abs(int(sdict['width'].replace('px', ''))),
            abs(int(sdict['height'].replace('px', '')))
        ]

        print(f'{self.direction} = {max(vals)}d ... {self.top},{self.left}')

        return max(vals)


class RobotRebaser:

    def __init__(self):
        self.driver = webdriver.Chrome(ChromeDriverManager().install())
        self._width = None
        self._height = None
        self._robot_origins = None

    def __del__(self):
        self.driver.close()
    
    @property
    def redo_button(self):
        return self.driver.find_element_by_class_name('redo')
    
    @property
    def soup(self):
        return BeautifulSoup(self.driver.page_source, 'html.parser')
    
    @property
    def robots(self):
        robots = {}

        robot_containers = self.driver.find_elements_by_class_name('robot-container')
        for rc in robot_containers:
            robot = Robot(self.driver, rc) 
            robots[robot.color] = robot      

        return robots
    
    @property
    def goal(self):
        goal_container = self.driver.find_element_by_class_name('goal-container')
        goal = Goal(self.driver, goal_container)
        return goal
    
    def reload(self):
        self.driver.get(URL)
        time.sleep(2)
        canvas = self.driver.find_element_by_tag_name('canvas')
        self._width = int(canvas.get_attribute('width'))
        self._height = int(canvas.get_attribute('height'))

        robots = self.robots
        goal = self.goal

    def force_one_color(self):

        path = []
        color = self.goal.color
        vmap = {}
        last_coord = None
        last_direction = None
        last_dest = None
        invalid = None

        coord = None
        visited = set()
        visited.add(self.robots[color].coord)

        #

        # where the robot actually goes based on arrow coords
        arrow_position_map = {}

        while True:
            print(f'VISITED: {visited}')
            print(f'CURRENTLY AT {self.robots[color].coord}')
            print(f'GOAL AT {self.goal.coord}')
            #print(f'PATH: {path}')

            if last_coord:
                traveled = get_distance(last_coord, self.robots[color].coord)
                print(f'TRAVELED: {traveled}')
                if traveled == 0.0:
                    invalid = last_direction


            # don't keep going nowhere
            if invalid is None:
                if last_direction and last_coord and self.robots[color].coord:
                    invalid = last_direction
                else:
                    invalid = None

            #print('click on the color')
            self.robots[color].click()

            #if self.robots[color].coord == coord:
            #    import epdb; epdb.st()

            coord = self.robots[color].coord
            last_coord = self.robots[color].coord
            if last_dest is not None:
                arrow_position_map[last_dest] = coord

            #if path and path[-1] == coord:
            #    self.redo_button.click()
            #    continue

            path.append(coord)
            visited.add(coord)

            distances = [(
                x.distance,
                x.coord,
                x.direction
            ) for x in self.robots[color].arrows.values()]


            '''
            ds = sorted([x[0] for x in distances])
            if sorted(set(ds)) != ds:
                import epdb; epdb.st()
            '''

            if self.goal.coord in [x[1] for x in distances]:
                print('I WIN!!!')
                distances = [x for x in distances if x[1] == self.goal.coord]
                self.robots[color].arrows[dmax[2]].click()
                break
                #import epdb; epdb.st()

            '''
            # eliminate any directions that take us to a previous point ...
            distances = [x for x in distances if x[1] not in visited]
            distances = [x for x in distances if x[1] != self.robots[color].coord]
            distances = [x for x in distances if x[1] not in vmap]
            '''

            # don't go to the same place
            distances = [x for x in distances if x[1] not in arrow_position_map]

            # don't go to the bad place
            if invalid:
                distances = [x for x in distances if x[2] != invalid]

            # don't go back and forth
            if last_direction is not None:
                distances = [x for x in distances if not is_opposite_direction(last_direction, x[2])]

            if not distances:
                print("NO WHERE TO GO 1!!!")
                break

            maxd = max([x[0] for x in distances])
            if len([x for x in distances if x[0] == maxd]) > 1:
                chosen = random.choice(distances)
                distances = [chosen]

            # stop if no place left to go
            if not distances:
                print("NO WHERE TO GO 2!!!")
                break

            pprint(distances)
            dmax = max(distances)
            last_dest = dmax[1]

            #print('click on the color')
            #self.robots[color].click()
            time.sleep(.2)
            print(f'going {dmax[2]} to {dmax[1]}')

            #self.robots[color].arrows[dmax[2]].click()
            #visited.add(dmax[1])
            
            last_direction = dmax[2]
            try:
                self.robots[color].arrows[dmax[2]].click()
                #last_direction = dmax[2]
                visited.add(dmax[1])
                vmap[dmax[1]] = self.robots[color].coord
            except Exception as e:
                continue

            time.sleep(.2)
            #visited.add(self.robots[color].coord)


        print("ARE WE DONE!?")
        import epdb; epdb.st()





def main():
    rr = RobotRebaser()
    rr.reload()
    rr.force_one_color()


if __name__ == "__main__":
    main()