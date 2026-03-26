from time import time, sleep
t = time()
from data import DataManager, saveToExcel, saveLifespanToExcel
from calc import Body, BodyManager
import numpy as np
import math
print("Imports done in", time()-t, "seconds")

G = 6.67430e-11
AU = 1.4965978707e11 # 1 astronomical unit in meters
YEAR = 31536000 # 1 year in seconds
m_sun = 1.989e30 # sun mass
m_earth = 5.972e24 # earth mass
m_moon = 7.3477e22 # moon mass
r_sun = 696.340e3
r_moon = 1.7374e3
r_earth = 6.371e3

#All bodies are written with z-coordinates but those are only there for the calculate_positions() method to function properly and to not break it. Ignore z-coordinates everywhere else, they do not impact simulation.
#All bodies are also written with radius but since the collision finder is not relevant anymore we just ignore this for now even though the data is still being saved and so on.
b4 = Body(m_earth, (0.0, 0.0, 0.0), (9.5e3, 0.0, 0.0), r_earth, "r", "Earth", )
b5 = Body(m_sun, (AU, 0.0, 0.0), (-5e3, -5e3, 0.0), r_sun, "b", "Sun1")
b6 = Body(m_sun, (AU/2, AU/2, 0.0), (0.0, 0.0, 0.0), r_sun, "y", "Sun2")

b45 = Body(m_sun, (0.0, 0.0, 0.0), (9.5e3, 0.0, 0.0), r_earth, "r", "Earth", )

b65 = Body(m_sun, (0.0, 0.0, 0.0), (9.5e3, 0.0, 0.0), r_earth, "r", "Test2", )
b7 = Body(m_sun, (AU, 0.0, 0.0), (-9.5e3, 0.0, 0.0), r_earth, "b", "Test3")
b8 = Body(10.0, (AU, AU, 0.0), (0.0, 0.0, 0.0), r_earth, "b", "Test1")

b9 = Body(m_sun/2, (AU/2, AU/2, 0.0), (0.0, 0.0, 0.0), r_sun, "y", "Sun2")

presets = {0: (b4, b5, b6),
           4: (b4, b5, b9),
           1: (b4, b7, b8),
           2: (b45, b5, b6)}

class Simulator:
    def __init__(self, start_bsys = 0, reset = False, t_start = 0, t_end = YEAR*1.5, positions = 2500, backup_freq = 1000):
        """
        start_bsys: 0 (default), 1 (test system)
        """
        self.start_bsys = presets[start_bsys]

        self.bodymgr = BodyManager(bodies=self.start_bsys)
        self.datamgr = DataManager(reset=reset, backup_freq=backup_freq)

        self.t_start = t_start
        self.t_end = t_end
        self.positions = positions

        self.sim_time = []
        self.last_sim_amount = 0
        
        #Used with start_analysis and analyse to keep track of last run parameters
        self.last_run = []
        self.first = True
    
    def run(self, sim_amount, show_latest = True, show_total = False, sim_track = None, lifespan = None):
        """
        Used for testing purposes. No analysing is done here.
        Sim_track is not used in this mode but user can set the values if they want.
        """
        for i in range(sim_amount):
            sim_time = self.bodymgr.calculate_positions(t_start=self.t_start, t_end=self.t_end, positions=self.positions)
            sim_data = self.bodymgr.getSimData()
            data = self.bodymgr_data_to_dict(sim_data)            

            ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(data["trajs"], data["vels"], data["mass"], self.t_start, self.t_end, data["pos"], save_acc=False, save_vel=False)

            self.datamgr.saveSim(2, sim_track, self.t_start, self.t_end, lifespan, sim_data, savemode=1)

            self.sim_time.append(sim_time)

        self.last_sim_amount = sim_amount

        self.datamgr.save_storage()

        self.print_stats(sim_amount=sim_amount, show_latest=show_latest, show_total=show_total)
        
    def start_analysis(self, **kwargs):
        """
        Same arguments as Simulator.analyse()
            mode = 0, system = [0,], amount = 10, track = 0, delta = 1000, delta_func = lambda var, delta: var + delta, var: str | list = "mass", positions = -1, start = -1, end = -1, show_latest = True, show_total = False

            Mode 0: start from new system
            Mode 1: continue from saved system in file on track with sim_id system[0]
            Mode 2: continue from last run on track 
            Mode 3: reset files and start from new system

            delta: How much to change var by.
            delta_func: How to change var. Default: new var = var + delta
            var: Variable to change between runs. mass, start_velocity, start_position, mass1, mass2, mass3

            returns: delta, delta_func, var, positions, start, end, show_latest, show_total

        Meant to be ran from terminal but also works in main script with input.

        g ID where ID is single integer (graph analyse manages the sim_id and makes it the correct form)

        A little bit limited since input() doesn't allow for variables to be put in
        """
        run = True
        while run:
            if not self.first:
                self.datamgr.save_storage()
                print("""n x system_preset delta vars - run x new sims on a new system on a new track. vars written as mass,start_velocity,start_position\n
                      cs x ID delta vars - continue to build upon an already saved system which is not the last\n
                      c x - continue on last system and track and run x amount of sims\n
                      g ID [a] [v] - graph-analysis of sim ID x with acceleration and velocity graphs (both optional)\n
                      e ID - save data from sim ID to an excel file\n
                      x - exit
                      """)
                inp = input()
 
                parsed = inp.split(" ")
                
                if parsed[0] == "c":
                    self.analyse(mode = 2, track = self.last_run[8], amount = int(parsed[1]), delta = self.last_run[0], delta_func=self.last_run[1], var=self.last_run[2], positions=self.last_run[3], start=self.last_run[4], end=self.last_run[5], show_latest=self.last_run[6], show_total=self.last_run[7])
                elif parsed[0] == "n":
                    self.analyse(mode = 0, amount = int(parsed[1]), system = [int(parsed[2]),], delta=int(parsed[3]), var=parsed[4].split(","))
                elif parsed[0] == "cs":
                    self.analyse(mode = 1, amount=int(parsed[1]), system=[int(parsed[2]),], delta=int(parsed[3]), var=parsed[4].split(","))
                elif parsed[0] == "g":
                    self.graph_analyse_sim(sim_id=[int(parsed[1]),], show_acc=len(parsed)>=3, show_vel=len(parsed)>=4)
                elif parsed[0] == "e":
                    self.save_excel(sim_id=int(parsed[1]))
                elif parsed[0] == "x":
                    return
            else:
                self.analyse(**kwargs)
                self.first = False

    def analyse(self, mode = 0, system = [0,], amount = 10, track = 0, delta = 1000, delta_func = lambda var, delta: var + delta, var: str | list = "mass", positions = -1, start = -1, end = -1, show_latest = True, show_total = False):
        """
        Mode 0: start from new system
        Mode 1: continue from saved system in file on track with sim_id system[0]
        Mode 2: continue from last run on track 
        Mode 3: reset files and start from new system
        Mode 4: continue from new track

        delta: How much to change var by.
        delta_func: How to change var. Default: new var = var + delta
        var: Variable to change between runs

        returns: delta, delta_func, var, positions, start, end, show_latest, show_total
        """
        
        if mode == 0 or mode == 3:
            if mode == 3:
                self.datamgr.reset()
            if len(system) == 1:
                self.set_sys(presets[system[0]])
            else:
                self.set_sys(bsys=system)
            
            if positions == -1: positions = self.positions
            if start == -1: start = self.t_start
            if end == -1: end = self.t_end
            track = self.datamgr.get_last_sim_track()+1
        
        elif mode == 1:
            data = self.datamgr.get_analyze_data(sim_id=system[0])

            bsys, data = self.data_to_bsys(data)

            self.set_sys(bsys=bsys)

            positions = int(data["steps"])
            start = int(data["sim_start"])
            end = int(data["sim_end"])
            track = data["sim_track"]

            if track == "Null": print("Error, sim_id", system[0], "does not contain a track, and therefore can't be continued."); return
        
        elif mode == 2:
            if not self.first and self.last_run == []: print("Error: no run found to continue from... returning"); return

            if len(system) == 1:
                self.set_sys(presets[system[0]])
            else:
                self.set_sys(bsys=system)

            data = self.datamgr.get_analyze_data()

            data = self.dataToDict(data)

            start = data["sim_start"]
            end = data["sim_end"]
            positions = data["steps"]
        
        elif mode == 4:
            track = self.datamgr.get_last_sim_track()+1

            self.set_sys(bsys=system)
        
        calc_times = []
        for i in range(amount):
            sim_time = self.bodymgr.calculate_positions(t_start=start, t_end=end, positions=positions)
            self.sim_time.append(sim_time)

            sim_data = self.bodymgr.getSimData()
            data = self.bodymgr_data_to_dict(sim_data)

            ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(data["trajs"], data["vels"], data["mass"], start, end, data["pos"], save_acc=False, save_vel=False)

            calc_times.append(calc_time)
            self.datamgr.saveSim(2, track, self.t_start, self.t_end, lifespan, sim_data, savemode=1)

            next_bsys = self.get_next_bsys(delta=delta, delta_func=delta_func, var=var)
            self.bodymgr.reset(next_bsys)

        self.last_sim_amount = amount
        self.print_stats(sim_amount=amount, show_latest=show_latest, show_total=show_total, calc_times=calc_times)
        self.last_run = [delta, delta_func, var, positions, start, end, show_latest, show_total, track]

    def test_calc(self):
        sim_time = self.bodymgr.calculate_positions(t_start=self.t_start, t_end=self.t_end, positions=self.positions)
        sim_data = self.bodymgr.getSimData()
        data = self.bodymgr_data_to_dict(sim_data)

        ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(data["trajs"], data["vels"], data["mass"], self.t_start, self.t_end, data["pos"], save_acc=False, save_vel=False)

        print(lifespan)

    def bodymgr_data_to_dict(self, data):
        trajs = data[0]

        #Removes z-coordinate and re-arranges the array so it consists of 6 arrays of 2000 coordinates (x, y, x, y, x, y)
        trajs_new = trajs[0][0], trajs[0][1], trajs[1][0], trajs[1][1], trajs[2][0], trajs[2][1]

        #Gives velocity in the correct format for use in lifespan calculator

        return_data = {
            "trajs": trajs_new,
            "vels": data[1],
            "pos": data[2],
            "start_pos": data[3],
            "startvel": data[4],
            "mass": data[5],
            "radius": data[6],
            "color": data[7],
            "label": data[8]
        }

        return return_data

    def data_to_bsys(self, data):
        """
        Data from parquet and h5 turned into three bodies and sorted data. Returns [[body1,body2,body3], sorted data]\n
        Sorted data with keys: Keys: sim_id, trajectory, velocity, sim_track, lifespan, sim_start, sim_end, start_velocity, start_position, steps, color, mass, label, radius,  \n
        Takes data directly from datamgr.
        """
        data = self.dataToDict(data)

        #Example body: b4 = Body(m_earth, (0.0, 0.0, 0.0), (9.5e3, 0.0, 0.0), r_earth, "r", "Earth", )
        m1, m2, m3 = data["mass"]
        sp1x, sp1y, sp2x, sp2y, sp3x, sp3y = data["start_position"]
        sv1x, sv1y, sv2x, sv2y, sv3x, sv3y = data["start_velocity"]
        r1, r2, r3 = data["radius"]
        c1, c2, c3 = data["color"]
        l1, l2, l3 = data["label"]

        b1 = Body(m1, [sp1x, sp1y, 0], [sv1x, sv1y, 0], r1, c1, l1)
        b2 = Body(m2, [sp2x, sp2y, 0], [sv2x, sv2y, 0], r2, c2, l2)
        b3 = Body(m3, [sp3x, sp3y, 0], [sv3x, sv3y, 0], r3, c3, l3)

        return [[b1, b2, b3], data]



    def start_analysis_FIRSTVERSION(self, mode = 0, start_id = [1,], start_sys = 0):
        #NOT IN USE AS I DO NOT HAVE TIME TO IMPLEMENT AUTOMATIC ANALYSIS!! ANALYSIS WILL BE DONE BY analyse()
        #Mode 0: reset data and start from the beginning
        #Mode 1: start on new track but with existing data
        #Mode 2: continue on existing but unfinished track

        if mode == 0:
            if self.datamgr.get_last_sim_id() != 0:
                self.reset()
            
            if start_sys == 0:
                #CONTINUE HERE
                pass

    
        elif mode == 1:
            data = self.datamgr.get_analyze_data(sim_id=start_id)
            data = self.dataToDict(data)

            ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(data["trajectory"], data["velocity"], data["mass"], data["sim_start"], data["sim_end"], data["steps"], save_acc=False, save_vel=False)

            print(lifespan)

    def save_excel(self, sim_id = 0):
        """
        Takes one sim_id and saves it as an excel file named accvel{sim_id}_{time()}.xlsx
        """
        data = self.datamgr.get_analyze_data(sim_id=0)
        data = self.dataToDict(data)

        velocity = data["velocity"]

        ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(data["trajectory"], [[velocity[0], velocity[1]],[velocity[2],velocity[3]],[velocity[4],velocity[5]]], data["mass"], data["sim_start"], data["sim_end"], data["steps"], save_acc=False, save_vel=False, analyse=False)

        saveToExcel(f"accvel{sim_id}_{time()}.xlsx", dataDict=data, accelerations=[ac1x, ac2x, ac3x, ac1y, ac2y, ac3y])

    def save_lifespan_excel(self, sim_track = 0, var: str = "mass"):
        """
        Takes one sim_track and saves its lifespan vs another variable of your choice, like for example "mass". 
        """
        data = self.datamgr.get_analyze_data(sim_track = sim_track, metadata=[var])
        saveLifespanToExcel(filename = f"lifespan{sim_track}_vs_other_{time()}.xlsx", dataDict=data, var=var)


    def print_stats(self, sim_amount, show_latest = True, show_total = False, calc_times = 0):
        last_sim_id = self.datamgr.get_last_sim_id()

        if show_latest:
            latest_sims = self.sim_time[-sim_amount:]
            latest_min_time = min(latest_sims)
            latest_max_time = max(latest_sims)

            latest_saves = self.datamgr.save_time[-max(math.floor(sim_amount/self.datamgr.storage_limit),1):]

            print("------------------------")
            print("----Latest stats:")
            print("New simulations run:", sim_amount)
            print("Average sim_time:", sum(latest_sims)/len(latest_sims))
            print("Fastest sim_time:", latest_min_time, "for sim_id(s):", [int(last_sim_id-(len(latest_sims)-index)) for index in [enum[0]+1 for enum in enumerate(latest_sims) if enum[1] == latest_min_time]])
            print("Slowest sim_time:", latest_max_time, "for sim_id(s):", [int(last_sim_id-(len(latest_sims)-index)) for index in [enum[0]+1 for enum in enumerate(latest_sims) if enum[1] == latest_max_time]])
            print("Average save_time:", sum(latest_saves)/len(latest_saves))
            if calc_times != 0: print("Average calc_time:", sum(calc_times)/len(calc_times))
            print("Total save_time:", sum(latest_saves))
            print("Total sim_time:", sum(latest_sims))
            if calc_times != 0: print("Total calc_time:", sum(calc_times))
            if calc_times != 0: print("Total runtime:", sum(latest_sims)+sum(latest_saves)+sum(calc_times))
            else: print("Total runtime:", sum(latest_sims)+sum(latest_saves))

        if show_total:
            total_sim_amount = len(self.sim_time)
            min_time = min(self.sim_time)
            max_time = max(self.sim_time)
            
            #currently does not support calc_time (no time to implement)
            print("----Total stats:")
            print("Total simulations run:", total_sim_amount)
            print("Average total sim_time:", sum(self.sim_time)/total_sim_amount)
            print("Fastest total sim_time:", min_time, "for sim_id(s):", [int(last_sim_id-(total_sim_amount-index)) for index in [enum[0]+1 for enum in enumerate(self.sim_time) if enum[1] == min_time]])
            print("Slowest total sim_time:", max_time, "for sim_id(s):", [int(last_sim_id-(total_sim_amount-index)) for index in [enum[0]+1 for enum in enumerate(self.sim_time) if enum[1] == max_time]])
            print("Average save_time:", sum(self.datamgr.save_time)/len(self.datamgr.save_time))
            print("Total save_time:", sum(self.datamgr.save_time))
            print("Total sim_time:", sum(self.sim_time))
            print("Total runtime:", sum(self.sim_time)+sum(self.datamgr.save_time))

    def get_next_bsys(self, delta = 1000, delta_func = lambda var, delta: var + delta, var: str | list = "mass"):
        #Body structure:
        #self.startpos = (startxyz[0], startxyz[1], startxyz[2])
        #self.startvel = startvelxyz
        #self.mass = mass
        #self.pos = self.startpos
        #self.vel = self.startvel
        #self.radius = radius
        #self.color = color
        #self.label = label
        #

        bodies = self.bodymgr.bodies

        if type(var) == str: var = [var,]

        for v in var:
            if v == "mass":
                for b in bodies:
                    b.mass = delta_func(b.mass, delta)
            elif v == "mass1":
                bodies[0].mass = delta_func(bodies[0].mass, delta)
            elif v == "mass2":
                bodies[1].mass = delta_func(bodies[1].mass, delta)
            elif v == "mass3":
                bodies[2].mass = delta_func(bodies[2].mass, delta)
            elif v == "start_position":
                for b in bodies:
                    p_list = []
                    for pos in b.startpos:
                        pos = delta_func(pos, delta)
                        p_list.append(pos)
                    b.startpos = p_list
            elif v == "start_velocity":
                for b in bodies:
                    v_list = []
                    for v in b.startvel:
                        v = delta_func(v, delta)
                        v_list.append(v)
                    b.startvel = v_list

        return (bodies)

    def get_bsys(self):
        for body in self.bodymgr.bodies:
            print(body)

    def get_last_sim_id(self): return self.datamgr.get_last_sim_id()

    def set_sys(self, bsys):
        self.bodymgr.reset(bodies = bsys)

    def reset(self, bsys = 0):
        if not bsys: bsys = self.start_bsys

        self.datamgr.reset()
        self.bodymgr.reset(bodies = bsys)
    
    def run_cycles(self, cycle_amount, sim_amount, show_latest = True, show_total = False):
            print("Running", cycle_amount, "cycles with", sim_amount, "sims in each")

            for i in range(cycle_amount):
                self.run(sim_amount, show_latest, show_total)
                print("Running next cycle in 5 seconds...")
                sleep(5)
            
            print(cycle_amount, "cycles done. With a total of", sim_amount*cycle_amount, "sims")

    #Calculates new trajectories and saves in bodymgr bsys.
    def calculate_positions(self):
        self.bodymgr.calculate_positions(self.t_end, self.positions)
    
    #Animates most recent trajectories stored in bsys.
    def start_animation(self):
        self.bodymgr.animate_trajectories()
    
    def save_log(self):
        if self.last_sim_amount == 0: print("No sims have been run yet"); return

        filename = str(time()) + "_log.txt"
        
        #Get log-variables
        last_sim_id = self.datamgr.get_last_sim_id()
        
        latest_sims = self.sim_time[-self.last_sim_amount:]
        latest_min_time = min(latest_sims)
        latest_max_time = max(latest_sims)

        latest_saves = self.datamgr.save_time[-math.floor(self.last_sim_amount/self.datamgr.storage_limit):]

        total_sim_amount = len(self.sim_time)
        min_time = min(self.sim_time)
        max_time = max(self.sim_time)

        with open(filename, "w") as f:
            f.write(f"""----Latest stats:\nNew simulations run: {self.last_sim_amount}\nAverage sim_time: {sum(latest_sims)/len(latest_sims)}\nFastest sim_time: {latest_min_time} for sim_id(s): {[int(last_sim_id-(len(latest_sims)-index)) for index in [enum[0]+1 for enum in enumerate(latest_sims) if enum[1] == latest_min_time]]}\nSlowest sim_time: {latest_max_time} for sim_id(s): {[int(last_sim_id-(len(latest_sims)-index)) for index in [enum[0]+1 for enum in enumerate(latest_sims) if enum[1] == latest_max_time]]}\nAverage save_time: {sum(latest_saves)/len(latest_saves)}\nTotal save_time: {sum(latest_saves)}\nTotal sim_time: {sum(latest_sims)}\nTotal runtime: {sum(latest_sims) + sum(latest_saves)}\n----Total stats:\nTotal simulations run: {total_sim_amount}\nAverage sim_time: {sum(self.sim_time)/total_sim_amount}\nFastest sim_time: {min_time} for sim_id(s): {[int(last_sim_id-(total_sim_amount-index)) for index in [enum[0]+1 for enum in enumerate(self.sim_time) if enum[1] == min_time]]}\nSlowest sim_time: {max_time} for sim_id(s): {[int(last_sim_id-(total_sim_amount-index)) for index in [enum[0]+1 for enum in enumerate(self.sim_time) if enum[1] == max_time]]}\nAverage save_time: {sum(self.datamgr.save_time)/len(self.datamgr.save_time)}\nTotal save_time: {sum(self.datamgr.save_time)}\nTotal sim_time: {sum(self.sim_time)}\nTotal runtime: {sum(self.sim_time)+sum(self.datamgr.save_time)}""")

        print(f"Log saved as '{filename}'")
    
    def h5dataToBodymgrTrajectory(self, data):
        """
        Index: index of trajectory to return. If index is set to "all", returns all sorted trajectories, but they can't be put directly into calculate_collisions
        Only takes 2D-data, z-coordinates are set to 0 
        """
        trajectories = data["trajectory"]
        return_data = []

        z = [0 for i in range(0,len(trajectories[0]))]
        for i in [0,2,4]:
            return_data.append([trajectories[i], trajectories[i+1], z])
        
        return return_data

    def dataToDict(self, data):
        """
        Cleans single data entry (trajectories and metadata from h5 and parquet) to a dict where keys correspond to data directly. Does not take data from multiple datasets (multiple sim_ids). 
        When retrieving data for cleaning, always include velocities and trajectories as well as metadata,

        Keys:
        sim_id,
        trajectory,
        velocity, 
        sim_track,
        lifespan,
        sim_start, 
        sim_end, 
        start_velocity, 
        start_position, 
        steps,
        color, 
        mass, 
        label, 
        radius, 
        """
        
        sim_id = next(iter(data[1]["sim_id"].values))
        trajectory = data[0][0][:6]
        #Velocity will be returned as an array of 6 elements, which is not how lifespan calculator wants it so before using it for that purpose make sure to cut it like: velocity = [[velocities[0], velocities[1]],[velocities[2],velocities[3]],[velocities[4],velocities[5]]]
        velocity= data[0][0][6:]
        sim_start = next(iter(data[1]["sim_start"].values))
        sim_end = next(iter(data[1]["sim_end"].values))
        start_velocity = next(iter(data[1]["start_velocity"].values))
        start_position = next(iter(data[1]["start_position"].values))
        color = next(iter(data[1]["color"].values))
        mass = next(iter(data[1]["mass"].values))
        label = next(iter(data[1]["label"].values))
        radius = next(iter(data[1]["radius"].values))
        steps = next(iter(data[1]["steps"].values))

        try:
            sim_track = int(next(iter(data[1]["sim_track"].values)))
            lifespan = next(iter(data[1]["lifespan"].values))
        except:
            sim_track = "Null"
            lifespan = "Null"
        
        cleaned_data = {"sim_id": sim_id,
                        "trajectory": trajectory, 
                        "velocity": velocity,
                        "sim_track": sim_track,
                        "lifespan": lifespan,
                        "sim_start": sim_start,
                        "sim_end": sim_end,
                        "start_velocity": start_velocity,
                        "start_position": start_position,
                        "steps": int(steps),
                        "color": color,
                        "mass": mass,
                        "label": label,
                        "radius": radius,
                        }
        
        return cleaned_data

    def graph_analyse_sim(self, sim_id = 0, DARK = True, show_acc = True, show_vel = True):
        """
        Default sim_id = 0 => last sim id
        """

        data = self.datamgr.get_analyze_data(sim_id=sim_id)
        data = self.dataToDict(data)

        sim_id = data["sim_id"]
        trajectory = data["trajectory"]
        velocity = data["velocity"]
        sim_start = data["sim_start"]
        sim_end = data["sim_end"]
        sim_track = data["sim_track"]
        lifespan = data["lifespan"]
        steps = data["steps"]
        start_velocity = data["start_velocity"]
        start_position = data["start_position"]
        colors = data["color"]
        mass = data["mass"]
        labels = data["label"]
        radius = data["radius"]


        #-------Matplotlib
        d = time()
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider, Button
        from  matplotlib.ticker import ScalarFormatter
        print("matplotlib import time:", time()-d)
        d = time()

        if DARK: plt.style.use('dark_background')
        
        fig = plt.figure(figsize=(10,8),num="Sim analysis")

        #If we use plt here we will by accident have two different axes which means we will have
        #one more axis than intended. To fix this, use either plt or ax and not both.
        ax = fig.add_subplot(111)

        ax.set_title(f"Three-Body Problem analysis of Sim ID {sim_id}")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")

        secaxx = ax.secondary_xaxis('top', functions=(lambda x: x/AU, lambda x: x*AU))
        secaxx.set_xlabel('x (AU)')
        secaxy = ax.secondary_yaxis("right", functions=(lambda x: x/AU, lambda x: x*AU))
        secaxy.set_ylabel('y (AU)')

        fig.subplots_adjust(left=0.35, bottom=0.25)

        ac1x, ac2x, ac3x, ac1y, ac2y, ac3y, lifespan, calc_time = self.bodymgr.calculate_lifespan(trajectories=trajectory, velocities=[[velocity[0], velocity[1]],[velocity[2],velocity[3]],[velocity[4],velocity[5]]], mass=mass, t_start=sim_start, t_end=sim_end, steps=steps, save_acc=False, save_vel=False)

        if show_acc and show_vel:
            fig2 = plt.figure(figsize=(10,8),constrained_layout=True, num="Acceleration")
            fig3 = plt.figure(figsize=(10,8),constrained_layout=True, num="Velocity")

            step_list = np.arange(1, steps+1)

            axac1x, axac2x, axac3x = fig2.add_subplot(3,2,1), fig2.add_subplot(3,2,3), fig2.add_subplot(3,2,5)
            axac1y, axac2y, axac3y = fig2.add_subplot(3,2,2), fig2.add_subplot(3,2,4), fig2.add_subplot(3,2,6)
            axv1x, axv2x, axv3x = fig3.add_subplot(3,2,1), fig3.add_subplot(3,2,3), fig3.add_subplot(3,2,5)
            axv1y, axv2y, axv3y = fig3.add_subplot(3,2,2), fig3.add_subplot(3,2,4), fig3.add_subplot(3,2,6)

            #axvlist and scvlist is ordered weirdly to match upp with the indexes of velocity array
            axalist = [axac1x, axac2x, axac3x, axac1y, axac2y, axac3y]
            axvlist = [axv1x, axv1y, axv2x, axv2y, axv3x, axv3y]

            sca1 = axac1x.scatter(step_list, ac1x)
            sca2 = axac2x.scatter(step_list, ac2x)
            sca3 = axac3x.scatter(step_list, ac3x)
            sca4 = axac1y.scatter(step_list, ac1y)
            sca5 = axac2y.scatter(step_list, ac2y)
            sca6 = axac3y.scatter(step_list, ac3y)
            scv1 = axv1x.scatter(step_list, velocity[0])
            scv2 = axv2x.scatter(step_list, velocity[2])
            scv3 = axv3x.scatter(step_list, velocity[4])
            scv4 = axv1y.scatter(step_list, velocity[1])
            scv5 = axv2y.scatter(step_list, velocity[3])
            scv6 = axv3y.scatter(step_list, velocity[5])
            
            aclist = [ac1x, ac2x, ac3x, ac1y, ac2y, ac3y]
            scalist = [sca1, sca2, sca3, sca4, sca5, sca6]
            scvlist = [scv1, scv4, scv2, scv5, scv3, scv6]

            #Bruh zoom is terrible
            class Zoom:
                def __init__(self):
                    self.current_zoom = 0
                
                def getZoom(self): return self.current_zoom
                def increaseZoom(self, amount): self.current_zoom+=amount
                def decreaseZoom(self, amount): self.current_zoom-=amount

            zoom = Zoom()

            class Zoom_button:
                def __init__(self, zoom_mode, fig_num, zoom_amount = 200):
                    """
                    Zoom_mode = 0 => zoom in. = 1 => zoom out
                    Zoom_amount: number of steps to zoom (remove zoom_amount/2 from both sides of data)
                    """
                    self.zoom_mode = zoom_mode
                    self.zoom_amount = zoom_amount

                    self.fig_num = fig_num

                def on_clicked(self, event):
                    if self.zoom_mode == 0 and zoom.getZoom()!=steps/2:
                        zoom.increaseZoom(self.zoom_amount)
                        
                        start = int(zoom.getZoom()/2)
                        end = int(steps-zoom.getZoom()/2)
                        if self.fig_num == 2:
                            for i, scatter in enumerate(scalist):
                                step_cut = step_list[start: end]
                                acc_cut = aclist[i][start: end]
                                offsets = list(zip(step_cut, acc_cut))
                                scatter.set_offsets(offsets)

                                axalist[i].set_xlim(step_cut[0], step_cut[-1])
                                axalist[i].set_ylim(min(acc_cut), max(acc_cut))
                                axalist[i].autoscale_view()
                            fig2.canvas.draw_idle()

                        elif self.fig_num == 3:
                            for i, scatter in enumerate(scvlist):
                                step_cut = step_list[start: end]
                                vel_cut = velocity[i][start: end]
                                offsets = list(zip(step_cut, vel_cut))
                                scatter.set_offsets(offsets)

                                axvlist[i].set_xlim(step_cut[0], step_cut[-1])
                                axvlist[i].set_ylim(min(vel_cut), max(vel_cut))
                                axvlist[i].autoscale_view()
                            fig3.canvas.draw_idle()
                        
                        return

                    if self.zoom_mode == 1 and zoom.getZoom() != 0:
                        zoom.decreaseZoom(self.zoom_amount)
                        start = int(zoom.getZoom()/2)
                        end = int(steps-zoom.getZoom()/2)

                        if self.fig_num == 2:
                            for i, scatter in enumerate(scalist):
                                step_cut = step_list[start: end]
                                acc_cut = aclist[i][start: end]
                                offsets = list(zip(step_cut, acc_cut))
                                scatter.set_offsets(offsets)

                                axalist[i].set_xlim(step_cut[0], step_cut[-1])
                                axalist[i].set_ylim(min(acc_cut), max(acc_cut))
                                axalist[i].autoscale_view()
                            fig2.canvas.draw_idle()

                        elif self.fig_num == 3:
                            for i, scatter in enumerate(scvlist):
                                step_cut = step_list[start: end]
                                vel_cut = velocity[i][start: end]
                                offsets = list(zip(step_cut, vel_cut))
                                scatter.set_offsets(offsets)

                                axvlist[i].set_xlim(step_cut[0], step_cut[-1])
                                axvlist[i].set_ylim(min(vel_cut), max(vel_cut))
                                axvlist[i].autoscale_view()
                            fig3.canvas.draw_idle()
            
            zoomina = Zoom_button(zoom_mode=0, fig_num=2)
            zoomouta = Zoom_button(zoom_mode=1, fig_num=2)

            zoominv = Zoom_button(zoom_mode=0, fig_num=3)
            zoomoutv = Zoom_button(zoom_mode=1, fig_num=3)

            zooma_ax1, zooma_ax2 = fig2.add_axes([0.505, 0.33, 0.03, 0.03]), fig2.add_axes([0.54, 0.33, 0.03, 0.03])
            zoomv_ax1, zoomv_ax2 = fig3.add_axes([0.505, 0.33, 0.03, 0.03]), fig3.add_axes([0.54, 0.33, 0.03, 0.03])

            zoomina_button = Button(zooma_ax1, "+",color="black", hovercolor="gray")
            zoomouta_button = Button(zooma_ax2, "-",color="black", hovercolor="gray")

            zoominv_button = Button(zoomv_ax1, "+",color="black", hovercolor="gray")
            zoomoutv_button = Button(zoomv_ax2, "-",color="black", hovercolor="gray")

            zoomina_button.on_clicked(zoomina.on_clicked)
            zoomouta_button.on_clicked(zoomouta.on_clicked)
            zoominv_button.on_clicked(zoominv.on_clicked)
            zoomoutv_button.on_clicked(zoomoutv.on_clicked)

            print("Layout of acc and vel graphs:\na1x, a1y\na2x, a2y\na3x, a3y\n\nv1x, v1y\nv2x, v2y\nv3x, v3y")

        time_slider_ax = fig.add_axes([0.3, 0.15, 0.65, 0.03], facecolor="red")
        time_slider = Slider(time_slider_ax, "Step", 1, steps, valinit=1)

        trajectory_button_ax = fig.add_axes([0.1, 0.25, 0.125, 0.05])
        trajectory_button = Button(trajectory_button_ax, "Toggle trajectory", color="black", hovercolor="gray")

        screenshot_button_ax = fig.add_axes([0.1, 0.18, 0.125, 0.05])
        screenshot_button = Button(screenshot_button_ax, "Save trajectory", color="black", hovercolor="gray")

        screenshot_button2_ax = fig.add_axes([0.1, 0.115, 0.125, 0.05])
        screenshot_button2 = Button(screenshot_button2_ax, "Save analysis", color="black", hovercolor="gray")

        scatter = ax.scatter([trajectory[0][0], trajectory[2][0], trajectory[4][0]], [trajectory[1][0], trajectory[3][0], trajectory[5][0]], c=colors)

        coords_button_ax = fig.add_axes([0.1, 0.055, 0.125, 0.045])
        coords_button = Button(coords_button_ax, "AU/XYZ", color="black", hovercolor="gray")

        def slider_on_changed(val):
            #Val is always a float, but we round it since the value displayed in
            #the matplotlib window is also rounded in the same way. This way the 
            #displayed value will be the same as the frame number shown.
            #It's also important here to use set_offsets instead of constantly re-drawing scatter points to make the slider smooth.
            
            val_rounded = round(val)
            i = val_rounded-1

            scatter.set_offsets([[trajectory[0][i], trajectory[1][i]], [trajectory[2][i], trajectory[3][i]], [trajectory[4][i], trajectory[5][i]]])

            fig.canvas.draw_idle()
        
        #Take screenshot of trajectory
        def screenshot_on_clicked(event):
            filename = f'trajectory{time()}.png'
            extent = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
            fig.savefig(filename, bbox_inches=extent.expanded(1.24, 1.175))
            print(f"Screenshot saved as '{filename}'")
        
        #Take screenshot of whole analysis screen
        def screenshot_on_clicked2(event):
            filename = f'trajectory{time()}.png'
            trajectory_button_ax.set_visible(False)
            screenshot_button_ax.set_visible(False)
            screenshot_button2_ax.set_visible(False)
            coords_button_ax.set_visible(False)
            fig.savefig(filename)
            trajectory_button_ax.set_visible(True)
            screenshot_button_ax.set_visible(True)
            screenshot_button2_ax.set_visible(True)
            coords_button_ax.set_visible(True)
            print(f"Screenshot saved as '{filename}'")
        
        class Trajectory_button:
            def __init__(self):
                #True - trajectories are displayed. False - trajectories are not displayed
                self.state = True
                self.plots = []

                for j in np.arange(0,5,2):
                    self.plots.append(ax.plot(trajectory[j], trajectory[j+1], c=colors[int(j/2)]))

            def button_on_clicked(self, event):
                if self.state:
                    for plot in self.plots:
                        for line in plot:
                            line.remove()
                    self.plots = []
                    self.state = False
                else:
                    for j in np.arange(0,5,2):
                        self.plots.append(ax.plot(trajectory[j], trajectory[j+1], c=colors[int(j/2)]))
                    self.state = True
                fig.canvas.draw_idle()

        class Coords_button:
            def __init__(self, positions):
                #states: "AU", "xyz"
                self.state = "AU"

                self.ax = fig.add_axes([0, 0.325, 0.2, 0.2])
                self.ax.set_axis_off()

                self.positions_au = [f"{position/AU} AU" for position in positions]
                self.positions_xyz = [f"{position} m" for position in positions]

                self.positions = self.positions_au

                self.text = self.ax.text(0.05, 0, f"Sim ID: {sim_id}\nSim track: {sim_track}\nLifespan: {round(lifespan[0]), lifespan[1]}\n\n\n{colors[0]}: {labels[0]} B1\n   {round(mass[0],8)} kg\n   x: {self.positions[0]}\n   y: {self.positions[1]}\n   {start_velocity[0]}, {start_velocity[1]} m/s\n\n{colors[1]}: {labels[1]} B2\n   {mass[1]} kg\n   x: {self.positions[2]}\n   y: {self.positions[3]}\n   {start_velocity[2]}, {start_velocity[3]} m/s\n\n{colors[2]}: {labels[2]} B3\n   {mass[2]} kg\n   x: {self.positions[4]}\n   y: {self.positions[5]}\n   {start_velocity[4]}, {start_velocity[5]} m/s\n\nSteps: {steps}",size="x-large")
                
            
            def button_on_clicked(self, event):
                if self.state == "AU":
                    self.positions = self.positions_xyz
                    self.state = "xyz"
                
                elif self.state == "xyz":
                    self.positions = self.positions_au
                    self.state = "AU"
                
                self.text.remove()

                self.text = self.ax.text(0.05, 0, f"Sim ID: {sim_id}\nSim track: {sim_track}\nLifespan: {round(lifespan[0]), lifespan[1]}\n\n\n{colors[0]}: {labels[0]} B1\n   {round(mass[0],8)} kg\n   x: {self.positions[0]}\n   y: {self.positions[1]}\n   {start_velocity[0]}, {start_velocity[1]} m/s\n\n{colors[1]}: {labels[1]} B2\n   {mass[1]} kg\n   x: {self.positions[2]}\n   y: {self.positions[3]}\n   {start_velocity[2]}, {start_velocity[3]} m/s\n\n{colors[2]}: {labels[2]} B3\n   {mass[2]} kg\n   x: {self.positions[4]}\n   y: {self.positions[5]}\n   {start_velocity[4]}, {start_velocity[5]} m/s\n\nSteps: {steps}",size="x-large")
                fig.canvas.draw_idle()

        time_slider.on_changed(slider_on_changed)
        screenshot_button.on_clicked(screenshot_on_clicked)
        screenshot_button2.on_clicked(screenshot_on_clicked2)
        traj_button = Trajectory_button()
        trajectory_button.on_clicked(traj_button.button_on_clicked)
        coo_button = Coords_button(start_position)
        coords_button.on_clicked(coo_button.button_on_clicked)

        print("matplotlib setup time:", time()-d)
        plt.show()

if __name__ == "__main__":
    #datamgr = DataManager(reset=False)
    #print(datamgr.get_analyze_data(metadata=["mass"], sim_id=[1,2,3]))

    sim = Simulator(start_bsys=0, reset=False)

    #sim.run(1, sim_track=1)
    #sim.graph_analyse_sim(show_acc=False, show_vel=False)

    #sim.start_analysis(mode = 1, system=[0,], delta = 5e29, var="mass")

    sim.save_lifespan_excel(1)
    
    #sim.save_excel()

