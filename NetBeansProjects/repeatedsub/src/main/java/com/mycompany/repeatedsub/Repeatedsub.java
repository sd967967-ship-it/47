/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.repeatedsub;

/**
 *
 * @author sd967
 */


import java.util.*;
public class Repeatedsub {
    Scanner in=new Scanner (System.in);
    String str="";
    void input()
    {
        System.out.println("enter a string");
        str=in.nextLine();
        
                
    }
    char ch;
    char n;
    void find()
    {
        for(int i=0;i<=str.length();i++)
        {
            ch=str.charAt(i);
            for(int j=0;j<=str.length();j++)
            {
                n=str.charAt(j);
            }
            
        }
    }

    public static void main(String[] args) {
        
    }
}
